# Contexthub Apps 통합 테스트 리스트

이 문서는 저장소(`Contexthub-Apps`) 내에 포함된 모든 미니앱의 리스트입니다. 각 앱의 작동 여부를 테스트하고 상태를 기록하기 위해 작성되었습니다.

## 📋 테스트 방법
1. 각 앱 폴더의 `main.py`를 실행하거나 Contexthub 런타임에서 실행합니다.
2. GUI가 정상적으로 출력되는지, 주요 기능이 작동하는지 확인합니다.
3. 테스트 결과를 **상태** 열에 기록합니다. (예: ✅ 정상, ❌ 오류, ⚠️ 부분작동)

---

## 🏗️ 3D Tools (3d)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Auto LOD](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/auto_lod) (`auto_lod`) | GUI | LOD 컨트롤이 포함된 메쉬 저해상도 변체 생성 | [ ] |
| [CAD to OBJ](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/cad_to_obj) (`cad_to_obj`) | GUI (Mini) | CAD 파일을 OBJ로 변환 | [ ] |
| [Extract Textures](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/extract_textures) (`extract_textures`) | GUI (Mini) | 3D 파일에서 내장 텍스처 추출 | [ ] |
| [Mesh Convert](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/mesh_convert) (`mesh_convert`) | GUI | 블렌더를 사용한 메쉬 파일 일괄 변환 | [ ] |
| [Open with Mayo](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/open_with_mayo) (`open_with_mayo`) | GUI (Mini) | 3D 파일을 Mayo에서 열기 확인 | [ ] |

## 🤖 AI Tools (ai)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Marigold PBR](file:///c:/Users/HG/Documents/Contexthub-Apps/ai/marigold_pbr) (`marigold_pbr`) | GUI | 단일 이미지에서 PBR 맵(Albedo, Normal, Depth) 생성 | [ ] |
| [Meeting Notes AI](file:///c:/Users/HG/Documents/Contexthub-Apps/ai/subtitle_qc) (`subtitle_qc`) | GUI | 회의 녹취록 작성 및 요약/결정사항 정리 | [ ] |

## ⚡ AI Lite (ai_lite)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [VersusUp](file:///c:/Users/HG/Documents/Contexthub-Apps/ai_lite/versus_up) (`versus_up`) | GUI | 가중치 스코어링 및 Ollama Vision 기반 의사결정 지원 | [ ] |

## 🔊 Audio Tools (audio)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Audio Toolbox](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/audio_toolbox) (`audio_toolbox`) | GUI | 줄기 분리, 음량 정규화, 포맷 변환 통합 도구 | [ ] |
| [Compress Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/compress_audio) (`compress_audio`) | GUI | 음질 유지하며 오디오 파일 크기 압축 | [ ] |

## 🎨 ComfyUI Tools (comfyui)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [ComfyUI Dashboard](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/comfyui_dashboard) (`comfyui_dashboard`) | GUI | ComfyUI 실행/중지/열기 대시보드 | [ ] |
| [Creative Studio (Advanced)](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/creative_studio_advanced) (`creative_studio_advanced`) | GUI | Checkpoint, LoRA, SUPIR 지원 전문 워크스페이스 | [ ] |
| [Creative Studio (Z)](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/creative_studio_z) (`creative_studio_z`) | GUI | 프롬프트 레이어 및 아이콘 생성 통합 워크스페이스 | [ ] |
| [AI Image Enhancer](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/image_enhancer) (`image_enhancer`) | GUI | 페인팅/레이어 기반 이미지 보정 워크벤치 | [ ] |
| [Inpainting Tools](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/inpainting) (`inpainting`) | GUI | ComfyUI 기반 인페인팅 및 마스크 도구 | [ ] |

## 📄 Document Tools (document)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Convert Docs](file:///c:/Users/HG/Documents/Contexthub-Apps/document/doc_convert) (`doc_convert`) | GUI (Mini) | 문서 파일 포맷 변환 | [ ] |
| [Document Scanner](file:///c:/Users/HG/Documents/Contexthub-Apps/document/doc_scan) (`doc_scan`) | GUI | 문서 이미지 스캔 및 왜곡 보정 | [ ] |

## 🖼️ Image Tools (image)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Blur To Gray32 EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/blur_gray32_exr) (`blur_gray32_exr`) | GUI (Mini) | 이미지를 그레이스케일 Float32 EXR로 변환 | [ ] |
| [Compare Images](file:///c:/Users/HG/Documents/Contexthub-Apps/image/image_compare) (`image_compare`) | GUI | 이미지 전후 비교 및 차이점 검사 | [ ] |
| [Merge to EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/merge_to_exr) (`merge_to_exr`) | GUI | 이미지 채널 결합 및 EXR 내보내기 | [ ] |
| [RigReady Vectorizer](file:///c:/Users/HG/Documents/Contexthub-Apps/image/rigreader_vectorizer) (`rigreader_vectorizer`) | GUI | 이미지에서 클린 라인/마스크 셰이프 추출(벡터화) | [ ] |
| [Split EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/split_exr) (`split_exr`) | GUI (Mini) | EXR 레이어 분리 저장 | [ ] |
| [Texture Packer ORM](file:///c:/Users/HG/Documents/Contexthub-Apps/image/texture_packer_orm) (`texture_packer_orm`) | GUI | ORM(Occlusion, Roughness, Metallic) 텍스처 패킹 | [ ] |

## 🛠️ Utilities (utilities)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |

| [Video Downloader](file:///c:/Users/HG/Documents/Contexthub-Apps/utilities/youtube_downloader) (`youtube_downloader`) | GUI | yt-dlp 기반 유튜브 비디오/오디오 다운로더 | [ ] |

---
*마지막 업데이트: 2026-04-27*
