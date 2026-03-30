from __future__ import annotations

import math
import struct

from .auto_lod_inspect import PreviewMesh
from .auto_lod_viewport_state import ViewportState, fit_view, reset_view

try:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMatrix4x4, QMouseEvent, QVector3D, QWheelEvent
    from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram, QOpenGLVertexArrayObject
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except ImportError as exc:
    raise ImportError("PySide6 OpenGL modules are required for the Auto LOD OpenGL preview viewport.") from exc


GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_DEPTH_TEST = 0x0B71
GL_CULL_FACE = 0x0B44
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_FLOAT = 0x1406
GL_LINES = 0x0001
GL_TRIANGLES = 0x0004

VERTEX_SHADER = """
attribute vec3 position;
attribute vec3 normal;
uniform mat4 mvp_matrix;
uniform mat4 model_matrix;
uniform vec3 light_direction;
varying float diffuse_value;
void main() {
    vec3 n = normalize((model_matrix * vec4(normal, 0.0)).xyz);
    diffuse_value = max(dot(n, normalize(-light_direction)), 0.15);
    gl_Position = mvp_matrix * vec4(position, 1.0);
}
"""

FRAGMENT_SHADER = """
uniform vec3 base_color;
uniform float alpha_value;
varying float diffuse_value;
void main() {
    vec3 shaded = base_color * diffuse_value;
    gl_FragColor = vec4(shaded, alpha_value);
}
"""

GRID_VERTEX_SHADER = """
attribute vec3 position;
uniform mat4 mvp_matrix;
uniform vec3 line_color;
varying vec3 color_value;
void main() {
    color_value = line_color;
    gl_Position = mvp_matrix * vec4(position, 1.0);
}
"""

GRID_FRAGMENT_SHADER = """
varying vec3 color_value;
void main() {
    gl_FragColor = vec4(color_value, 1.0);
}
"""


class OpenGlMeshViewport(QOpenGLWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(420)
        self._mesh: PreviewMesh | None = None
        self._message = "Load an OBJ, STL, or PLY mesh to preview it here."
        self._viewport_state = ViewportState()
        self._last_pos: QPointF | None = None
        self._pan_active = False
        self._program: QOpenGLShaderProgram | None = None
        self._line_program: QOpenGLShaderProgram | None = None
        self._mesh_vao: QOpenGLVertexArrayObject | None = None
        self._mesh_buffer: QOpenGLBuffer | None = None
        self._mesh_vertex_count = 0
        self._grid_vao: QOpenGLVertexArrayObject | None = None
        self._grid_buffer: QOpenGLBuffer | None = None
        self._grid_vertex_count = 0
        self._axis_vao: QOpenGLVertexArrayObject | None = None
        self._axis_buffer: QOpenGLBuffer | None = None
        self._axis_vertex_count = 0
        self._gl = None

    def set_preview_mesh(self, mesh: PreviewMesh | None, message: str) -> None:
        self._mesh = mesh
        self._message = message
        self.makeCurrent()
        self._destroy_mesh_buffers()
        if self.context() is not None and self._mesh is not None and self._gl is not None:
            self._upload_mesh()
        self.doneCurrent()
        self.update()

    def set_wireframe(self, enabled: bool) -> None:
        self._viewport_state.wireframe = enabled
        self.update()

    def reset_camera(self) -> None:
        reset_view(self._viewport_state)
        self.update()

    def fit_camera(self) -> None:
        fit_view(self._viewport_state)
        self.update()

    def initializeGL(self) -> None:
        self._gl = self.context().functions()
        self._gl.initializeOpenGLFunctions()
        self._gl.glEnable(GL_DEPTH_TEST)
        self._gl.glEnable(GL_CULL_FACE)
        self._gl.glEnable(GL_BLEND)
        self._gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._init_programs()
        self._init_reference_buffers()
        if self._mesh is not None:
            self._upload_mesh()

    def resizeGL(self, width: int, height: int) -> None:
        if self._gl is not None:
            self._gl.glViewport(0, 0, max(width, 1), max(height, 1))

    def paintGL(self) -> None:
        if self._gl is None:
            return
        self._gl.glClearColor(0.07, 0.09, 0.12, 1.0)
        self._gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        projection = QMatrix4x4()
        aspect = max(self.width(), 1) / max(self.height(), 1)
        projection.perspective(42.0, aspect, 0.1, 200.0)
        view = self._view_matrix()
        self._draw_reference_lines(projection, view)
        self._draw_mesh(projection, view)

    def _view_matrix(self) -> QMatrix4x4:
        center = QVector3D(0.0, 0.0, 0.0)
        distance = self._camera_distance()
        yaw = math.radians(self._viewport_state.yaw_degrees)
        pitch = math.radians(self._viewport_state.pitch_degrees)
        eye = QVector3D(
            math.cos(pitch) * math.cos(yaw) * distance,
            math.sin(pitch) * distance,
            math.cos(pitch) * math.sin(yaw) * distance,
        )
        eye += QVector3D(self._viewport_state.pan_x, self._viewport_state.pan_y, 0.0)
        center += QVector3D(self._viewport_state.pan_x, self._viewport_state.pan_y, 0.0)
        view = QMatrix4x4()
        view.lookAt(eye, center, QVector3D(0.0, 1.0, 0.0))
        return view

    def _camera_distance(self) -> float:
        radius = 1.0
        if self._mesh is not None:
            radius = max(self._mesh.bounds.radius, 0.5)
        return radius * self._viewport_state.distance_scale + 1.5

    def _init_programs(self) -> None:
        self._program = QOpenGLShaderProgram(self)
        self._program.addShaderFromSourceCode(QOpenGLShader.Vertex, VERTEX_SHADER)
        self._program.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAGMENT_SHADER)
        self._program.link()

        self._line_program = QOpenGLShaderProgram(self)
        self._line_program.addShaderFromSourceCode(QOpenGLShader.Vertex, GRID_VERTEX_SHADER)
        self._line_program.addShaderFromSourceCode(QOpenGLShader.Fragment, GRID_FRAGMENT_SHADER)
        self._line_program.link()

    def _init_reference_buffers(self) -> None:
        grid_vertices: list[float] = []
        for index in range(-10, 11):
            value = index / 2.0
            grid_vertices.extend([value, 0.0, -5.0, value, 0.0, 5.0])
            grid_vertices.extend([-5.0, 0.0, value, 5.0, 0.0, value])
        axis_vertices = [
            0.0, 0.0, 0.0, 1.2, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 1.2, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 1.2,
        ]
        self._grid_vao, self._grid_buffer, self._grid_vertex_count = self._create_line_buffer(grid_vertices)
        self._axis_vao, self._axis_buffer, self._axis_vertex_count = self._create_line_buffer(axis_vertices)

    def _create_line_buffer(self, values: list[float]) -> tuple[QOpenGLVertexArrayObject, QOpenGLBuffer, int]:
        vao = QOpenGLVertexArrayObject(self)
        vao.create()
        buffer = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        buffer.create()
        vao.bind()
        buffer.bind()
        data = struct.pack(f"<{len(values)}f", *values)
        buffer.allocate(data, len(data))
        self._line_program.bind()
        self._line_program.enableAttributeArray("position")
        self._line_program.setAttributeBuffer("position", GL_FLOAT, 0, 3, 3 * 4)
        buffer.release()
        vao.release()
        return vao, buffer, len(values) // 3

    def _upload_mesh(self) -> None:
        if self._mesh is None or self._program is None:
            return
        self._destroy_mesh_buffers()
        payload = build_mesh_payload(self._mesh)
        self._mesh_vertex_count = len(payload) // 6
        self._mesh_vao = QOpenGLVertexArrayObject(self)
        self._mesh_vao.create()
        self._mesh_buffer = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._mesh_buffer.create()
        self._mesh_vao.bind()
        self._mesh_buffer.bind()
        data = struct.pack(f"<{len(payload)}f", *payload)
        self._mesh_buffer.allocate(data, len(data))
        self._program.bind()
        self._program.enableAttributeArray("position")
        self._program.enableAttributeArray("normal")
        self._program.setAttributeBuffer("position", GL_FLOAT, 0, 3, 6 * 4)
        self._program.setAttributeBuffer("normal", GL_FLOAT, 3 * 4, 3, 6 * 4)
        self._mesh_buffer.release()
        self._mesh_vao.release()

    def _destroy_mesh_buffers(self) -> None:
        if self._mesh_buffer is not None:
            self._mesh_buffer.destroy()
            self._mesh_buffer = None
        if self._mesh_vao is not None:
            self._mesh_vao.destroy()
            self._mesh_vao = None
        self._mesh_vertex_count = 0

    def _draw_mesh(self, projection: QMatrix4x4, view: QMatrix4x4) -> None:
        if self._mesh_vao is None or self._program is None or self._mesh_vertex_count <= 0:
            return
        bounds = self._mesh.bounds
        model = QMatrix4x4()
        model.translate(-bounds.center[0], -bounds.center[1], -bounds.center[2])
        mvp = projection * view * model
        self._program.bind()
        self._program.setUniformValue("mvp_matrix", mvp)
        self._program.setUniformValue("model_matrix", model)
        self._program.setUniformValue("light_direction", QVector3D(-0.4, -0.7, -0.3))
        self._program.setUniformValue("base_color", QVector3D(0.62, 0.87, 1.0))
        self._program.setUniformValue("alpha_value", 1.0)
        self._mesh_vao.bind()
        mode = GL_LINES if self._viewport_state.wireframe else GL_TRIANGLES
        self._gl.glDrawArrays(mode, 0, self._mesh_vertex_count)
        self._mesh_vao.release()
        self._program.release()

    def _draw_reference_lines(self, projection: QMatrix4x4, view: QMatrix4x4) -> None:
        if self._line_program is None:
            return
        identity = QMatrix4x4()
        mvp = projection * view * identity
        self._line_program.bind()
        self._line_program.setUniformValue("mvp_matrix", mvp)
        if self._grid_vao is not None:
            self._line_program.setUniformValue("line_color", QVector3D(0.22, 0.26, 0.32))
            self._grid_vao.bind()
            self._gl.glDrawArrays(GL_LINES, 0, self._grid_vertex_count)
            self._grid_vao.release()
        if self._axis_vao is not None:
            for offset, color in ((0, QVector3D(0.96, 0.42, 0.38)), (2, QVector3D(0.37, 0.82, 0.52)), (4, QVector3D(0.42, 0.67, 0.98))):
                self._line_program.setUniformValue("line_color", color)
                self._axis_vao.bind()
                self._gl.glDrawArrays(GL_LINES, offset, 2)
                self._axis_vao.release()
        self._line_program.release()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in {Qt.LeftButton, Qt.RightButton}:
            self._last_pos = event.position()
            self._pan_active = event.button() == Qt.RightButton or bool(event.modifiers() & Qt.ShiftModifier)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._last_pos is None:
            super().mouseMoveEvent(event)
            return
        delta = event.position() - self._last_pos
        self._last_pos = event.position()
        if self._pan_active:
            self._viewport_state.pan_x += delta.x() * 0.005
            self._viewport_state.pan_y -= delta.y() * 0.005
        else:
            self._viewport_state.yaw_degrees += delta.x() * 0.6
            self._viewport_state.pitch_degrees = max(-89.0, min(89.0, self._viewport_state.pitch_degrees + delta.y() * 0.5))
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in {Qt.LeftButton, Qt.RightButton}:
            self._last_pos = None
            self._pan_active = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta:
            factor = 0.88 if delta > 0 else 1.12
            self._viewport_state.distance_scale = max(1.2, min(10.0, self._viewport_state.distance_scale * factor))
            self.update()
            event.accept()
            return
        super().wheelEvent(event)


def build_mesh_payload(mesh: PreviewMesh) -> list[float]:
    payload: list[float] = []
    for a, b, c in mesh.faces:
        va = QVector3D(*mesh.vertices[a])
        vb = QVector3D(*mesh.vertices[b])
        vc = QVector3D(*mesh.vertices[c])
        normal = QVector3D.crossProduct(vb - va, vc - va).normalized()
        for vertex in (va, vb, vc):
            payload.extend([vertex.x(), vertex.y(), vertex.z(), normal.x(), normal.y(), normal.z()])
    return payload
