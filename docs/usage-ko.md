# UK Regulation Helpdesk — Windows 사용법

**[RegulationHelpdesk.exe 다운로드](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe)** · [GitHub Pages 채팅 화면](https://swk99.github.io/data-regulation-helpdesk-uk/) · [공개 릴리스](https://github.com/swk99/data-regulation-helpdesk-uk/releases)

GitHub Pages에서 질문하고, 내 Windows PC에서 자료 검색·저장과 AI 답변 생성을 처리하는 앱입니다. 사용 중에는 PC와 실행 프로그램이 켜져 있어야 합니다.

## 1. 처음 한 번 준비하기

- **Windows x64 PC**에서 사용합니다.
- [Ollama for Windows](https://ollama.com/download/windows)를 설치하고 실행하세요. 이미 설치되어 있다면 다시 설치하지 않아도 됩니다.
- 위 링크에서 **RegulationHelpdesk.exe**를 다운로드하세요. Python은 실행 파일에 포함되어 있습니다. Python, Node.js, Docker, WSL, 소스 코드 ZIP은 별도로 필요하지 않습니다.
- 공식 자료 조회와 처음 모델을 내려받을 때 인터넷이 필요합니다. 모델 다운로드에는 수 GB의 저장 공간이 필요할 수 있으며, 속도와 메모리 사용량은 PC와 선택된 모델에 따라 달라집니다.

이 EXE는 개인 프로젝트용 미서명 실행 파일입니다. Windows 또는 회사 보안 정책이 실행을 제한할 수 있습니다. 회사 PC에서 정책에 의해 차단되면 IT 담당자에게 확인하세요. [릴리스에 함께 올라온 SHA-256 체크섬](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/SHA256SUMS.txt)으로 다운로드 파일을 확인할 수 있습니다.

## 2. 실행하고 질문하기

1. **RegulationHelpdesk.exe를 더블클릭**하세요.
2. 검은 실행 창에서 초기 준비를 진행합니다. 설치된 지원 모델을 우선 사용하며, 없는 모델만 내려받습니다. `qwen3.5:4b`가 설치되어 있다면 우선 사용합니다.
3. **`Helpdesk ready`**가 나오면 GitHub Pages가 자동으로 열립니다. 그 탭을 사용하세요.
4. 브라우저에서 **로컬 장치 접근 / 로컬 네트워크 접근**을 물으면 이 사이트에 허용하세요. 주소나 토큰을 복사해 넣을 필요는 없습니다.
5. `Hello.`를 보내 연결을 확인하세요. 인사에는 규제 자료를 검색하지 않고 사용 안내를 반환합니다.
6. 구체적인 규제 질문을 입력하세요. 예: `What are the PRA expectations for model risk management?`
7. 답변의 출처 제목·문서 구간·URL·확인 시점을 함께 확인하세요. 처음에는 인덱스가 비어 있어 자료를 찾고 저장하는 데 시간이 걸릴 수 있습니다.

**사용 중에는 EXE 실행 창을 닫지 마세요.** 종료하려면 실행 창에서 `Ctrl + C`를 누르거나 창을 닫으세요. 다음에 사용할 때는 EXE를 다시 실행하면 됩니다.

## 3. 업데이트하기

1. 기존 **RegulationHelpdesk.exe 실행 창을 닫습니다.**
2. [최신 EXE](https://github.com/swk99/data-regulation-helpdesk-uk/releases/latest/download/RegulationHelpdesk.exe)를 다운로드합니다.
3. 새로 받은 EXE를 실행합니다. 이전 다운로드 파일과 혼동하지 않도록 확인하세요.
4. 자동으로 열린 GitHub Pages에서 **`Ctrl + Shift + R`**을 눌러 최신 화면을 불러옵니다.

문서 인덱스는 `%LOCALAPPDATA%\UKRegulationHelpdesk\data`에 저장되므로 EXE를 교체해도 유지됩니다. 새 실행 세션은 새 연결 정보를 사용하므로 이전 탭보다 새로 열린 탭을 이용하세요.

`windows-4-1`에는 질문 처리 중 발생하던 문서 후보 검색 SQL 오류 수정이 포함되어 있습니다. 이전 버전의 해당 오류는 페이지 새로고침만으로 해결되지 않으므로 EXE를 업데이트해야 합니다.

## 4. 연결·실행 문제 해결

| 화면 또는 증상 | 확인할 사항 |
| --- | --- |
| 실행 중인데 설치·연결 안내가 나옴 | EXE가 자동으로 열어준 탭에서 `Ctrl + Shift + R` 후 **Retry connection**을 누르세요. 원래 탭을 닫았다면 EXE 창을 닫고 다시 실행하세요. |
| Ollama만 실행 중 | **RegulationHelpdesk.exe도 실행**해야 합니다. Ollama 자체는 이 프로젝트의 자료 검색 API를 시작하지 않습니다. |
| `Failed to fetch` 또는 읽을 수 없는 응답 | 먼저 최신 EXE인지 확인하세요. 기존 실행 창을 닫고 새 EXE로 교체하세요. 계속되면 실행 창의 마지막 오류를 확인하세요. |
| `Cannot reach the PC app` | EXE 창이 열려 있고 `Helpdesk ready`가 표시되는지, 브라우저가 이 사이트의 로컬 장치 접근을 허용했는지 확인한 뒤 재시도하세요. |
| `Launch link expired` | EXE를 닫고 다시 실행하세요. 연결 링크는 한 번만 사용할 수 있고 5분 후 만료됩니다. |
| `already running` | 기존 실행 창을 사용하거나 닫은 뒤 한 번만 다시 실행하세요. |
| 모델 다운로드 또는 Ollama 오류 | Ollama 앱이 실행되는지, 인터넷과 저장 공간이 충분한지 확인하세요. 실행 창에 실패 원인이 표시됩니다. |
| 답변 대신 출처만 표시됨 | 충분한 근거를 확인하지 못했거나 모델 출력 검증에 실패한 경우입니다. 제시된 문서를 확인하고 질문을 더 구체적으로 작성하세요. |
| PC 앱 내부 오류와 `support ID` 표시 | 실행 창에서 같은 ID의 오류를 찾아 마지막 오류 내용을 확인하세요. |

회사 정책이나 브라우저가 GitHub Pages의 로컬 연결을 허용하지 않는 경우, EXE가 있는 폴더에서 PowerShell을 열고 아래 명령으로 화면도 로컬에서 실행할 수 있습니다.

```powershell
.\RegulationHelpdesk.exe --local
```

## 5. 확인 범위와 데이터 저장

- 규제 질문마다 허용된 공식 자료의 갱신을 확인하려고 시도합니다. 모든 규제 사이트를 빠짐없이 실시간 검색하는 서비스는 아닙니다.
- 영국 날짜는 PC 시계를 바탕으로 Europe/London 기준으로 계산합니다. Windows 날짜·시간 동기화를 켜두세요.
- FCA 일반 사이트 자료의 인덱싱은 이용 조건에 따른 허가 확인이 필요하며, FCA Handbook 접근에도 제한이 있습니다. 사용할 수 없는 출처를 확인한 것처럼 표시하지 않습니다.
- 자료를 오늘 가져왔다는 사실만으로 해당 규정이 오늘 법적으로 적용된다고 단정하지 않습니다. 답변의 근거와 적용일을 원문에서 확인하세요.
- 모델 추론과 문서 인덱스는 내 PC에서 처리합니다. 공개 GitHub 저장소와 릴리스에는 소스 코드·실행 파일·사용 문서를 제공합니다.
- 채팅에 고객 정보, 은행 내부 기밀 또는 비밀번호를 입력하지 마세요.

## 6. 개발자용 자료

[README](../README.md) · [영문 실행 가이드](local-windows.md) · [구조 설명](architecture.md) · [출처 확인과 제한](source-verification.md)

Windows CI는 소스 코드 테스트 후 EXE를 만들고, 실행 파일 자체에서 시작·자동 인증·인사·규제 질문 처리·벡터 저장 검사를 수행한 뒤 공개 릴리스를 올립니다. 이 자동 검사는 외부 서비스에 모의 응답을 사용하므로, 개별 PC의 실제 Ollama 성능이나 규제 답변의 정확성을 보증하는 것은 아닙니다.
