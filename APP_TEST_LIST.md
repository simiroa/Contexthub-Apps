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
| [Blender Bake GUI](file:///c:/Users/HG/Documents/Contexthub-Apps/3d/blender_bake_gui) (`blender_bake_gui`) | GUI | 블렌더 기반 텍스처 베이킹 도구 | [ ] |
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
| [AI Text Lab](file:///c:/Users/HG/Documents/Contexthub-Apps/ai_lite/ai_text_lab) (`ai_text_lab`) | GUI | Gemini/Ollama를 사용한 텍스트 분석/번역 워크스페이스 | [ ] |
| [VersusUp](file:///c:/Users/HG/Documents/Contexthub-Apps/ai_lite/versus_up) (`versus_up`) | GUI | 가중치 스코어링 및 Ollama Vision 기반 의사결정 지원 | [ ] |

## 🔊 Audio Tools (audio)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Audio Toolbox](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/audio_toolbox) (`audio_toolbox`) | GUI | 줄기 분리, 음량 정규화, 포맷 변환 통합 도구 | [ ] |
| [Compress Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/compress_audio) (`compress_audio`) | GUI | 음질 유지하며 오디오 파일 크기 압축 | [ ] |
| [Convert Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/convert_audio) (`convert_audio`) | GUI | MP3, WAV, FLAC, M4A 고속 변환 | [ ] |
| [Enhance Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/enhance_audio) (`enhance_audio`) | GUI | 노이즈 제거 및 음성 명료도 향상 | [ ] |
| [Extract Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/extract_audio) (`extract_audio`) | GUI | 비디오에서 오디오 추출 및 보컬/배경음 분리 | [ ] |
| [Normalize Volume](file:///c:/Users/HG/Documents/Contexthub-Apps/audio/normalize_volume) (`normalize_volume`) | GUI | EBU R128 표준 기반 LUFS 음량 정규화 | [ ] |

## 🎨 ComfyUI Tools (comfyui)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [ComfyUI Dashboard](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/comfyui_dashboard) (`comfyui_dashboard`) | GUI | ComfyUI 실행/중지/열기 대시보드 | [ ] |
| [Creative Studio (Advanced)](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/creative_studio_advanced) (`creative_studio_advanced`) | GUI | Checkpoint, LoRA, SUPIR 지원 전문 워크스페이스 | [ ] |
| [Creative Studio (Z)](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/creative_studio_z) (`creative_studio_z`) | GUI | 프롬프트 레이어 및 아이콘 생성 통합 워크스페이스 | [ ] |
| [Inpainting Tools](file:///c:/Users/HG/Documents/Contexthub-Apps/comfyui/inpainting) (`inpainting`) | GUI | ComfyUI 기반 인페인팅 및 마스크 도구 | [ ] |

## 📄 Document Tools (document)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Convert Docs](file:///c:/Users/HG/Documents/Contexthub-Apps/document/doc_convert) (`doc_convert`) | GUI (Mini) | 문서 파일 포맷 변환 | [ ] |
| [Document Scanner](file:///c:/Users/HG/Documents/Contexthub-Apps/document/doc_scan) (`doc_scan`) | GUI | 문서 이미지 스캔 및 왜곡 보정 | [ ] |
| [PDF Merge](file:///c:/Users/HG/Documents/Contexthub-Apps/document/pdf_merge) (`pdf_merge`) | GUI (Mini) | PDF 파일 순서 변경 및 병합 | [ ] |
| [PDF Split](file:///c:/Users/HG/Documents/Contexthub-Apps/document/pdf_split) (`pdf_split`) | GUI (Mini) | PDF 파일 분할 및 개별 저장 | [ ] |

## 🖼️ Image Tools (image)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Blur To Gray32 EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/blur_gray32_exr) (`blur_gray32_exr`) | GUI (Mini) | 이미지를 그레이스케일 Float32 EXR로 변환 | [ ] |
| [Compare Images](file:///c:/Users/HG/Documents/Contexthub-Apps/image/image_compare) (`image_compare`) | GUI | 이미지 전후 비교 및 차이점 검사 | [ ] |
| [Image Convert](file:///c:/Users/HG/Documents/Contexthub-Apps/image/image_convert) (`image_convert`) | GUI (Mini) | 이미지 포맷 일괄 변환 | [ ] |
| [Image Resizer](file:///c:/Users/HG/Documents/Contexthub-Apps/image/image_resizer) (`image_resizer`) | GUI | 고성능 이미지 리사이징 및 일괄 처리 | [ ] |
| [Merge to EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/merge_to_exr) (`merge_to_exr`) | GUI | 이미지 채널 결합 및 EXR 내보내기 | [ ] |
| [Normal Flip Green](file:///c:/Users/HG/Documents/Contexthub-Apps/image/normal_flip_green) (`normal_flip_green`) | GUI (Mini) | 노멀맵의 그린 채널 반전 | [ ] |
| [RigReady Vectorizer](file:///c:/Users/HG/Documents/Contexthub-Apps/image/rigreader_vectorizer) (`rigreader_vectorizer`) | GUI | 이미지에서 클린 라인/마스크 셰이프 추출(벡터화) | [ ] |
| [Simple Normal Roughness](file:///c:/Users/HG/Documents/Contexthub-Apps/image/simple_normal_roughness) (`simple_normal_roughness`) | GUI (Mini) | 이미지를 노멀/러프니스 맵으로 변환 | [ ] |
| [Split EXR](file:///c:/Users/HG/Documents/Contexthub-Apps/image/split_exr) (`split_exr`) | GUI (Mini) | EXR 레이어 분리 저장 | [ ] |
| [Texture Packer ORM](file:///c:/Users/HG/Documents/Contexthub-Apps/image/texture_packer_orm) (`texture_packer_orm`) | GUI | ORM(Occlusion, Roughness, Metallic) 텍스처 패킹 | [ ] |

## 🛠️ Utilities (utilities)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |

| [Video Downloader](file:///c:/Users/HG/Documents/Contexthub-Apps/utilities/youtube_downloader) (`youtube_downloader`) | GUI | yt-dlp 기반 유튜브 비디오/오디오 다운로더 | [ ] |

## 🎬 Video Tools (video)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Create Proxy](file:///c:/Users/HG/Documents/Contexthub-Apps/video/create_proxy) (`create_proxy`) | GUI | 비디오 프록시 파일 생성 도구 | [ ] |
| [Interpolate 30fps](file:///c:/Users/HG/Documents/Contexthub-Apps/video/interpolate_30fps) (`interpolate_30fps`) | GUI (Mini) | 비디오 30fps 프레임 보간 | [ ] |
| [Remove Audio](file:///c:/Users/HG/Documents/Contexthub-Apps/video/remove_audio) (`remove_audio`) | GUI (Mini) | 비디오에서 오디오 스트림 제거 | [ ] |
| [Video Convert](file:///c:/Users/HG/Documents/Contexthub-Apps/video/video_convert) (`video_convert`) | GUI | FFmpeg 프리셋 기반 비디오 변환 | [ ] |

## 🏛️ Legacy / Others (legacyapp)
| 앱 이름 (ID) | 실행 모드 | 설명 | 상태 |
| :--- | :--- | :--- | :--- |
| [Qwen3 TTS](file:///c:/Users/HG/Documents/Contexthub-Apps/legacyapp/ai/qwen3_tts) (`qwen3_tts`) | GUI | Qwen3 기반 음성 합성 및 클로닝 | [ ] |
| [Whisper Subtitle AI](file:///c:/Users/HG/Documents/Contexthub-Apps/legacyapp/ai/whisper_subtitle) (`whisper_subtitle`) | GUI | Whisper 기반 자막 생성 및 세션 복구 | [ ] |

---
*마지막 업데이트: 2026-04-27*
