# GUI Design Report (2026-03-14)

기준 자료:
- 최신 캡처 로그: [gui_capture_log.md](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_capture_log.md)
- 캡처 루트: [gui_captures](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures)

평가 기준:
- 첫 화면만 보고도 앱의 목적과 다음 행동이 즉시 이해되는가
- 빈 상태가 불안정해 보이지 않고, 입력 기대치가 명확한가
- 주요 CTA가 시야의 끝에서 잘리지 않고 자연스럽게 보이는가
- 에러/준비 상태가 단순 기술 메시지가 아니라 작업 관점에서 해석되는가

## 총평

현재 포팅본은 `다크 테마`, `라운드 카드`, `푸른 CTA`라는 공통 언어는 어느 정도 맞춰졌습니다. 다만 앱별 완성도 편차가 큽니다. 가장 안정적인 축은 `qwen3_tts`, `youtube_downloader`, `texture_packer_orm`, `doc_scan`이고, 가장 위험한 축은 `video_convert`, `versus_up`, `blender_bake_gui`, `cad_to_obj`, `mesh_convert`처럼 첫 화면이 사실상 에러 화면인 앱들입니다.

반복되는 공통 문제:
- 빈 상태 패널이 너무 커서 “미완성 화면”처럼 보임
- 파일 리스트 영역과 실제 설정 영역의 비중이 맞지 않음
- 상태 문구가 `Ready` 수준에 머물러 작업 맥락이 약함
- 일부 앱은 캡처 성공이어도 시각적으로는 에러 상태임
- 앱 제목, 안내문, CTA 사이의 위계가 카테고리별로 들쭉날쭉함

우선순위:
1. 에러 화면 상태 앱을 디자인 평가 대상이 아닌 “차단 이슈”로 먼저 분류
2. 빈 상태 레이아웃을 실제 작업 흐름 중심으로 재구성
3. 공통 상태 바와 액션 바를 더 강하게 규격화

## AI

### qwen3_tts
- 캡처: [qwen3_tts.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai/qwen3_tts.png)
- 평가: 현재 전체 앱 중 가장 서비스다운 화면입니다. 상단 상태, 말풍선 리스트, 입력 구역, 하단 액션이 작업 흐름과 맞습니다.
- 장점: 프로필 색 구분이 직관적이고, “대화형 TTS”라는 성격이 첫 화면에 드러납니다.
- 문제: 좌우 폭이 다소 넓어 실제 입력 밀도보다 화면이 퍼져 보입니다. 상단 설명 카드의 높이도 약간 큽니다.
- 제안: 창 기본 폭을 줄이고, 상단 상태 카드를 더 압축해 대화 버블 영역에 집중도를 주는 편이 좋습니다.

### esrgan_upscale
- 캡처: [esrgan_upscale.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai/esrgan_upscale.png)
- 평가: 구조는 정리됐지만 아직 “빈 프리뷰 박스가 과도하게 큰 툴”처럼 보입니다.
- 장점: 설정과 모델 상태가 오른쪽으로 분리돼 의사결정은 빠릅니다.
- 문제: 좌측 회색 입력 영역이 너무 커서 거대한 빈 캔버스처럼 보입니다. 하단 액션 바가 내용 위에 얹힌 느낌도 강합니다.
- 제안: 파일 카드 높이를 줄이고, 썸네일+파일명 리스트 중심으로 바꾸는 것이 좋습니다. 모델 상태 카드도 경고 배지형으로 더 압축할 수 있습니다.

### rmbg_background
- 캡처: [rmbg_background.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai/rmbg_background.png)
- 평가: `esrgan_upscale`와 동일하게 기본 구조는 맞지만, 실제 사용감은 아직 미완성입니다.
- 장점: 모델 선택, 후처리, 투명 PNG 옵션이 한 묶음으로 이해됩니다.
- 문제: 좌측 대상 이미지 영역이 지나치게 크고 비어 있어 “무언가 깨진 상태”로 느껴질 수 있습니다.
- 제안: 좌측은 드롭존+최근 파일 리스트 정도로 축소하고, 오른쪽에는 출력 예시나 배경 제거 품질 안내를 넣는 편이 설득력이 높습니다.

### demucs_stems
- 캡처: [demucs_stems.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai/demucs_stems.png)
- 평가: 기능 배치는 안정적이지만, 정보 밀도와 시각 리듬이 부족합니다.
- 장점: 파일, 설정, 로그, 진행 바, CTA라는 생산형 도구의 기본 구조는 갖췄습니다.
- 문제: 세로 공간이 많이 비고, 폼 필드 폭이 균형 없이 커 보입니다. “처리 중: 0...” 로그는 신뢰감이 약합니다.
- 제안: 파일 리스트와 로그 높이를 줄이고, 분리 모델/형식/모드를 한 줄 툴바로 압축하면 훨씬 단단해집니다.

### whisper_subtitle
- 캡처: [whisper_subtitle.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai/whisper_subtitle.png)
- 평가: 정보는 많지만, 초보자에게는 다소 복잡해 보입니다.
- 장점: 모델, 작업, 장치, 언어, 출력 형식이 한 화면에서 모두 보입니다.
- 문제: 좌우 균형이 다소 어색하고, 다운로드 카드가 실제 입력 흐름을 끊습니다. 로그 토글도 위계가 약합니다.
- 제안: “입력 > 모델 준비 > 출력 형식 > 실행” 4단 흐름으로 재정렬하는 편이 낫습니다. 설치 필요 상태는 상단 경고 배너로 올리는 것이 좋습니다.

## AI Lite

### ai_text_lab
- 캡처: [ai_text_lab.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai_lite/ai_text_lab.png)
- 평가: 도구형 유틸리티로는 설계 방향이 괜찮습니다.
- 장점: 프리셋 선택, 모델 선택, 입력/결과 패널, 실행 버튼의 위치가 합리적입니다.
- 문제: 상단 바에 기능이 몰려 있고, `Model`, `Auto`, 핀/번개 아이콘의 의미가 초기 사용자에게 불명확합니다. `INPUT`, `RESULT` 라벨은 너무 작습니다.
- 제안: 상단 제어를 2줄로 나누고, 각 아이콘을 텍스트 버튼으로 바꾸거나 툴팁을 강화해야 합니다.

### versus_up
- 캡처: [versus_up.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/ai_lite/versus_up.png)
- 평가: 현재는 UX 평가 대상이 아니라 차단 이슈입니다.
- 장점: 없음. 첫 화면이 에러 상태입니다.
- 문제: 중앙 에러 토스트만 보이며, 사용자가 무엇을 해야 하는지 전혀 알 수 없습니다.
- 제안: 최소한 “의존성 누락”, “설정 키 없음”처럼 사람 기준 메시지로 바꾸고, 복구 액션 버튼을 제공해야 합니다.

## Audio

- 평가: 실행은 가능하지만, 상단이 너무 비어 있어 레이아웃 완성도가 낮습니다.
- 장점: 하단 CTA는 명확하고 변환 옵션도 이해하기 쉽습니다.
- 문제: 파일 영역이 거의 비가시적이고, 체크 옵션이 넓게 퍼져 있어 화면 집중력이 떨어집니다.
- 제안: 상단에 파일 리스트 카드를 명확히 만들고, 옵션은 하나의 설정 카드로 묶는 편이 좋습니다.

### extract_bgm
- 캡처: [extract_bgm.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/audio/extract_bgm.png)
- 평가: 기본 틀은 보이지만, 아직 “스캐폴드” 느낌이 강합니다.
- 장점: Separation/Settings 탭, 로그, CTA 구성은 작업 도구 문법에 맞습니다.
- 문제: 빈 상태가 너무 광활해 실제 기능보다 덜 완성돼 보입니다.
- 제안: 첫 화면에 지원 포맷, 예상 출력, 모델 설명을 요약해 넣고 파일 드롭존을 더 분명히 보여줘야 합니다.

### extract_voice
- 캡처: [extract_voice.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/audio/extract_voice.png)
- 평가: `extract_bgm`과 동일한 셸을 공유하는 것으로 보이며 같은 평가가 적용됩니다.
- 장점: 하단 실행 CTA는 명확합니다.
- 문제: 현재 캡처만 보면 `extract_bgm`과 거의 구분되지 않습니다.
- 제안: 보컬 추출 전용임이 드러나도록 제목 아래 설명과 기본 프리셋 문구를 차별화해야 합니다.

## Document

### doc_convert
- 캡처: [doc_convert.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/document/doc_convert.png)
- 평가: 단순 변환 도구로서는 꽤 안정적입니다.
- 장점: 입력 파일 수, 대상 형식, 일괄 변환 CTA가 자연스럽습니다.
- 문제: 상단의 큰 회색 입력 영역이 실제 정보 없이 너무 큽니다.
- 제안: 파일 목록 미리보기와 예상 출력 요약으로 대체하면 완성도가 크게 올라갑니다.

### doc_scan
- 캡처: [doc_scan.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/document/doc_scan.png)
- 평가: 현재 문서 앱 중 가장 목적 전달력이 좋습니다.
- 장점: 좌측 페이지 리스트, 중앙 프리뷰, 우측 도구 패널 구조가 명확합니다.
- 문제: 우측 툴 영역이 다소 빽빽하고, 저장/내보내기 섹션의 존재감이 약합니다.
- 제안: 작업 단계별로 도구를 접거나 그룹화하고, “다음 단계”를 더 강하게 표시하면 좋습니다.

### pdf_merge
- 캡처: [pdf_merge.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/document/pdf_merge.png)
- 평가: 매우 단순한 앱이라 흐름은 쉽지만, 화면이 비어 보여 품질 인상이 약해집니다.
- 장점: 경고 문구와 CTA는 이해하기 쉽습니다.
- 문제: 파일 리스트 외에 사용자가 붙잡을 시각적 기준점이 적습니다.
- 제안: 병합 순서 변경, 출력 파일명 예시, 드래그 안내를 추가하면 훨씬 실용적으로 보입니다.

### pdf_split
- 캡처: [pdf_split.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/document/pdf_split.png)
- 평가: `pdf_merge` 계열과 비슷한 장단점을 가질 가능성이 큽니다.
- 장점: 단일 목적 앱으로 이해되기 쉽습니다.
- 문제: 분할 규칙이 첫 화면에 충분히 드러나지 않으면 “무엇을 설정해야 하는지”가 모호해질 수 있습니다.
- 제안: 페이지 범위 프리셋, 미리보기 페이지 카운트, 출력 규칙 예시를 상단 카드로 올리는 것이 좋습니다.

## Image

### image_compare
- 캡처: [image_compare.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/image_compare.png)
- 평가: 비교 모드 버튼 구조는 좋지만, 아직 핵심 프리뷰가 너무 거칠게 보입니다.
- 장점: `Single`, `Split`, `Slider`, `Diff`는 사용자가 바로 이해할 수 있는 언어입니다.
- 문제: 회색 프리뷰 박스가 너무 크고 빈 상태 안내가 약합니다.
- 제안: 기본 상태에 “A/B 두 장 선택” 안내와 모드 설명을 오버레이로 넣어야 합니다.

### image_convert
- 캡처: [image_convert.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/image_convert.png)
- 평가: 기능은 명확하지만, 화면 자원의 대부분을 빈 입력 상자가 차지합니다.
- 장점: 일괄 변환 도구로서 의미는 바로 읽힙니다.
- 문제: 파일 카드보다 설정과 출력 예측이 더 중요함에도 현재는 비중이 반대입니다.
- 제안: 파일 리스트를 줄이고, 변환 옵션과 예상 결과 파일명을 더 강하게 보여주는 편이 좋습니다.

### merge_to_exr
- 캡처: [merge_to_exr.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/merge_to_exr.png)
- 평가: 기술 사용자 대상 도구라는 느낌은 나지만, 채널 매핑 정보가 한눈에 꽂히지는 않습니다.
- 장점: 전문 툴 분위기는 살아 있습니다.
- 문제: 레이어/패스 관계가 테이블이나 카드로 더 구조화될 필요가 있습니다.
- 제안: 채널 매핑을 행 단위 카드로 재구성하고, 활성 패스 수를 상단 요약으로 띄우는 것이 좋습니다.

### normal_flip_green
- 캡처: [normal_flip_green.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/normal_flip_green.png)
- 평가: mini confirm 도구로 해석하는 것이 맞습니다. 선택 수 확인 후 바로 콘솔 흐름으로 넘기는 짧은 작업에 적합합니다.
- 장점: 행동이 단순하고 오해 여지가 적습니다.
- 문제: 템플릿 분류와 문서가 이 mini 성격을 충분히 반영하지 못했습니다.
- 제안: mini confirm-shell 기준으로 유지하고, 출력 파일명 규칙과 간단한 작업 요약만 강조하면 됩니다.

### image_resizer
- 캡처: [image_resizer.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/image_resizer.png)
- 평가: 실무용 도구로서 방향은 좋습니다.
- 장점: “가장 긴 변 기준”과 같은 가이드 문구가 기능 이해에 도움을 줍니다.
- 문제: 설정 양에 비해 공간 배분이 불균형할 가능성이 높고, 결과 예측이 약합니다.
- 제안: 좌측 파일, 우측 설정, 하단 결과 요약의 3영역 구조를 더 선명히 만드는 것이 좋습니다.

### rigreader_vectorizer
- 캡처: [rigreader_vectorizer.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/rigreader_vectorizer.png)
- 평가: 고급 도구치고는 비교적 정리되어 있는 편입니다.
- 장점: 다단 정보 구조를 견딜 수 있는 레이아웃을 이미 갖췄습니다.
- 문제: 초보자에게는 설정량이 많아 진입 장벽이 높습니다.
- 제안: 기본/고급 설정 분리를 더 강하게 하고, 출력 예시를 상단에 노출하는 편이 좋습니다.

### simple_normal_roughness
- 캡처: [simple_normal_roughness.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/simple_normal_roughness.png)
- 평가: 의도는 좋지만 결과 프리뷰가 확실히 살아 있어야 가치가 전달되는 유형입니다.
- 장점: 원본/노멀/러프니스라는 분리 개념 자체는 직관적입니다.
- 문제: 빈 상태에서 보면 “무엇이 생성되는지”가 약합니다.
- 제안: 샘플 프리뷰 또는 현재 탭 결과 예시를 항상 보여줘야 합니다.

### split_exr
- 캡처: [split_exr.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/split_exr.png)
- 평가: 기능상 필요한 정보가 많아 구조화가 중요합니다.
- 장점: 채널 추출이라는 목적은 비교적 명확합니다.
- 문제: 추출 규칙과 결과 파일명의 관계가 약하게 보일 수 있습니다.
- 제안: 선택된 채널 수, 출력 파일 수, 파일명 규칙을 요약 카드로 먼저 보여주는 편이 좋습니다.

### texture_packer_orm
- 캡처: [texture_packer_orm.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/image/texture_packer_orm.png)
- 평가: 이미지 카테고리에서 가장 상품성이 높은 화면입니다.
- 장점: 채널 슬롯 구조가 즉시 이해되고, `ORM` 프리셋과 드롭존의 관계가 좋습니다.
- 문제: 하단 출력 영역이 다소 길고, 아이콘 버튼은 의미가 약합니다.
- 제안: 불러오기/비우기 액션을 좀 더 명시적으로 드러내고, 드롭존에 썸네일을 넣으면 마감 수준이 올라갑니다.

## 3D

### auto_lod
- 캡처: [auto_lod.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/3d/auto_lod.png)
- 평가: 이번 캡처 기준으로는 3D 카테고리에서 유일하게 제품다운 구조를 가집니다.
- 장점: 요약, 입력 파일, 작업 설정, 상태가 분리돼 있어 학습 비용이 낮습니다.
- 문제: 입력 파일 영역이 크고, 설정이 아직 설명 텍스트 수준에 머물러 있습니다.
- 제안: 실제 프리셋 편집 요소를 넣고, 입력 패널에는 드롭존과 최근 파일을 함께 보여주는 편이 좋습니다.

### blender_bake_gui
- 캡처: [blender_bake_gui.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/3d/blender_bake_gui.png)
- 평가: 현재는 디자인 평가보다 실행 차단 이슈가 우선입니다.
- 장점: 없음. 첫 화면이 에러 배너뿐입니다.
- 문제: 외부 도구 누락을 사용자 과실처럼 보이게 만드는 기술 메시지입니다.
- 제안: “Blender가 필요합니다” 형태의 안내 화면, 설치 경로 선택, 재시도 버튼이 필요합니다.

### cad_to_obj
- 캡처: [cad_to_obj.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/3d/cad_to_obj.png)
- 평가: 현재는 `blender_bake_gui`와 같은 차단 상태입니다.
- 장점: 없음.
- 문제: Mayo Converter 경로 에러가 그대로 노출됩니다.
- 제안: 전용 의존성 설정 화면으로 치환해야 하며, 현재 상태는 최종 사용자를 위한 UI가 아닙니다.

### mesh_convert
- 캡처: [mesh_convert.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/3d/mesh_convert.png)
- 평가: 역시 실행 차단 상태입니다.
- 장점: 없음.
- 문제: `cad_to_obj`와 동일한 오류 노출 패턴입니다.
- 제안: 공통 “외부 툴 필요” 온보딩 화면을 3D 앱 전체에 공유하는 것이 맞습니다.

## Utilities

### youtube_downloader
- 캡처: [youtube_downloader.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/utilities/youtube_downloader.png)
- 평가: 실사용성이 꽤 높습니다.
- 장점: URL 입력, 미디어 카드, 품질 선택, 저장 경로, 큐 추가/즉시 다운로드 흐름이 명확합니다.
- 문제: 하단 로그 영역과 `Update Engine` 링크의 위계가 약합니다. 일부 컨트롤 간 세로 간격도 약간 답답합니다.
- 제안: 다운로드 전 검증 상태를 카드 상단에 배지로 보여주고, 고급 옵션은 접어두는 것이 더 세련됩니다.

## Video

### video_convert
- 캡처: [video_convert.png](/C:/Users/HG/Documents/Contexthub-Apps/Diagnostics/gui_captures/video/video_convert.png)
- 평가: 현재는 디자인 평가 이전에 실행 차단 상태입니다.
- 장점: 없음.
- 문제: `Dropdown.__init__()` 오류가 그대로 노출되고 있으며, 사용자는 앱 목적조차 확인할 수 없습니다.
- 제안: 최소한 안전한 예외 경계 화면으로 감싸고, 기술 오류 대신 “초기화 실패”와 복구 방법을 안내해야 합니다.

## 결론

현재 기준선으로 삼을 만한 앱:
- `qwen3_tts`
- `texture_packer_orm`
- `doc_scan`
- `youtube_downloader`
- `auto_lod`

즉시 수정이 필요한 앱:
- `video_convert`
- `versus_up`
- `blender_bake_gui`
- `cad_to_obj`
- `mesh_convert`

공통 UX 작업으로 가장 효과가 큰 항목:
1. 빈 상태 패널 축소
2. 상태 문구를 작업 중심 언어로 변경
3. 에러 상태를 전용 온보딩/복구 화면으로 치환
4. 파일 기반 툴에서 드롭존과 결과 예측 카드 강화
