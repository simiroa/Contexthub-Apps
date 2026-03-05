# Doc Convert (문서 변환)

## 소개
PDF, Word, Excel, PowerPoint 등 다양한 문서 포맷을 상호 변환합니다.

## 지원 변환

| 입력 | 출력 | 설명 |
|------|-----|------|
| PDF | DOCX | 편집 가능한 Word 문서로 |
| PDF | XLSX | 표 추출하여 Excel로 |
| PDF | PPTX | 프레젠테이션으로 |
| PDF | Markdown | LLM 최적화 텍스트로 |
| PDF | Images | 페이지별 이미지로 |
| DOCX/PPTX | PDF | 범용 PDF로 |
| Markdown | PDF | 문서화 |

## 사용법

1. 문서 파일 선택 후 우클릭
2. **Document → Doc Convert** 선택
3. 출력 포맷 선택
4. 변환 완료까지 대기

## 고급 기능
- **OCR 모드**: 스캔된 PDF에서 텍스트 추출
- **표 추출**: PDF 내 표를 Excel로 정확히 변환
- **이미지 추출**: PDF 내 이미지만 별도 저장
- **마크다운 변환**: AI 분석용 텍스트 추출

## 의존성
- pdf2docx (PDF→Word)
- pymupdf (PDF 처리)
- python-pptx (PowerPoint)
- openpyxl (Excel)
