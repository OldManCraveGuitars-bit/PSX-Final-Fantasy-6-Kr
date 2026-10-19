# 개발 소스 안내

이 저장소는 V0.75-r1의 번역 원본·런타임 구현·패처·문장 관리기와 주요 검사 코드를 공개합니다. **원본 게임, BIOS, 추출된 실행 파일, 과거 개발 BIN, 로컬 에뮬레이터 브리지·검수 저장 상태는 제공하지 않습니다.** 따라서 모든 게임 페이로드를 새 체크아웃 하나에서 즉시 재생성하는 형태는 아닙니다.

## 디렉터리

| 경로 | 내용 |
| --- | --- |
| `native/` | C, MIPS assembly, 링크 배치 파일 |
| `tools/` | 편집·인코딩·추출·삽입·검사 코드의 개발 스냅샷 |
| `translations/` | 한글 번역과 항목별 레이아웃·검수 상태 |
| `analysis/*-original.json` | 문장 관리기가 쓰는 원문/분류/위치 메타데이터 |
| `assets/text-manager/` | 편집기용 갈무리 글꼴과 표시 폭 정보 |
| `patcher/` | 공개 패처와 통합 검사 소스 |
| `docs/verification/` | 공개 범위에 맞춰 로컬 경로를 정리한 검사 기록 |

과거 빌드 단계나 중간 후보를 참조하는 스크립트도 있으므로 모든 `build_*.py`를 순서 없이 실행하지 마세요. 최신 내부 기준은 `build_locke_job_fix.py`의 v085이며 해당 도구는 이전 로컬 빌드 결과와 추출물을 전제로 합니다.

`extract_disc.py`가 요구하는 PSX ISO 스캐너는 로컬 의존성입니다. 준비된 스캐너 경로를 `FF6_DISC_SCANNER` 환경변수로 지정하거나 `local-tools/scan_psx_disc.py`에 준비해야 합니다. 디스크 인벤토리, 원본 테이블과 툴체인 등 추가 로컬 입력도 필요합니다. 에뮬레이터를 직접 제어하는 QA 스크립트와 개인 검수 상태는 배포하지 않았습니다.

## 패처 EXE 재빌드

검증에 사용한 환경은 Windows x64, Python 3.13.15, PyInstaller 6.22.3입니다.

1. 릴리스의 xdelta ZIP에서 `FF6-KR-V0.75-r1.xdelta`와 `xdelta3.exe`를 `patcher/resources/`로 복사합니다.
2. 저장소의 `manifest.json`과 두 파일의 해시가 맞는지 확인합니다.
3. PyInstaller를 준비한 뒤 저장소 루트에서 빌드합니다.

```powershell
python -m pip install PyInstaller==6.22.3
python patcher/build_patcher.py
```

결과는 `dist/FF6-KR-Patcher-V0.75-r1.exe`입니다. 빌드 환경·경로에 따라 EXE 자체의 해시는 달라질 수 있지만 적용 결과 BIN은 매니페스트의 해시와 같아야 합니다.

실제 배포 EXE 통합 검사는 지원 원본을 지정해 실행합니다.

```powershell
python patcher/test_patcher.py --source "D:\Games\Final Fantasy VI (Japan).bin" --exe "dist\FF6-KR-Patcher-V0.75-r1.exe" --report "patcher-check.json"
```

검사는 임시 폴더에 결과와 변조 입력을 생성하고 원본 보존, 한글 경로, 거부 동작을 확인합니다. 원본 입력을 덮어쓰지 않습니다.

## 문장 관리기를 소스로 실행

Python, Tk와 Pillow가 있는 환경에서 다음과 같이 실행합니다. 준비된 폰트·메트릭을 읽으므로 일반 편집·검사에 게임 BIN을 직접 요구하지 않습니다.

```powershell
python tools/text_manager.py --project "."
python tools/text_manager.py --project "." --audit "layout-report.json"
```

기존 `build_text_manager.py`는 원본 추출물에서 메트릭을 다시 뽑는 단계도 실행합니다. 원본 추출물 없이 배포된 메트릭 그대로 EXE를 만들려면 다음처럼 패키징만 수행할 수 있습니다.

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name FF6KoreanTextManager --add-data "assets/text-manager;." tools/text_manager.py
```

갤러리 그림 미리보기, 신규 부록 문자열 등록의 원본 바이트 대조, 게임 삽입은 별도 로컬 자원을 요구합니다. 문장 관리기에서 변경한 내용은 고정된 공개 패치 EXE에 자동으로 반영되지 않습니다.

## 버전 대응

| 명칭 | 의미 |
| --- | --- |
| 공개 `V0.75-r1` / 태그 `v0.75-r1` | 이번 GitHub 배포 |
| 내부 `v085` | 직업 모험가 복원까지 반영한 최신 개발 기준 |
| 내부 `v075` | 과거 기능 검수 시점. 공개 V0.75-r1와 다른 이름 체계 |

초기 V0.75/v084 배포는 GitHub에 이력으로 유지하며 최신 수정판은 V0.75-r1/v085입니다.

스크린샷과 기존 보고서의 내부 번호는 증거 출처를 보존하기 위해 유지합니다. 공개 배포 번호만 보고 내부 번호가 되돌아갔다고 해석하지 마세요.

## 로컬 정리 이력

2026-10-20 작업 공간 정리에서 v079 이하의 과거 테스트 BIN/CUE 82쌍을 제거했습니다. 원본, 저장 데이터, 모든 빌드 메타데이터와 페이로드, v080–v085 이미지는 보존했습니다. 과거 테스트 스크립트가 삭제된 후보 BIN을 직접 요구하면 별도 재생성이 필요합니다.
