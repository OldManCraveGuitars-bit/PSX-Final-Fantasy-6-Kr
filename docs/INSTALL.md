# V0.75-r1 설치 방법

## 준비물

- Windows x64 PC에서 실행할 패처 ZIP.
- 보유한 PlayStation 일본판 FFVI **SLPM-86198**의 지원 원본 BIN.
- 출력 위치 약 400 MB 이상과 EXE 임시 압축 해제 공간.
- BIN/CUE를 실행할 수 있는 PSX 환경. 게임 원본과 BIOS는 배포물에 포함하지 않습니다.

원본 BIN은 **325,133,424 bytes**, SHA-256은 다음과 같아야 합니다.

```text
a607011d9c9442797ae155228e86e9dae6e503aaeb7dc9603ac552ffd8d036df
```

파일명은 달라도 내용이 같으면 됩니다. 다른 지역판·덤프·CHD·압축 파일·이미 한글화된 BIN에는 직접 적용하지 않습니다. `CUE`는 트랙 설명 파일이며 패처의 입력으로 고르는 파일은 `BIN`입니다.

## Windows 패처

1. 릴리스의 `FF6-KR-Patcher-V0.75-r1.zip`을 원하는 폴더에 풉니다.
2. `FF6-KR-Patcher-V0.75-r1.exe`를 실행합니다. 관리자 권한이나 Python 설치가 필요하지 않습니다.
3. **원본 일본판 BIN**의 찾아보기를 눌러 원본을 선택합니다.
4. **완성 파일을 저장할 폴더**를 선택합니다. 원본 폴더와 같아도 원본 파일은 덮어쓰지 않습니다.
5. **한글 패치 적용**을 누르고 완료 안내를 기다립니다.
6. 선택한 폴더 아래 새로 생긴 `FF6-KR-V0.75-r1` 폴더를 엽니다.

완성 파일:

```text
FF6-KR-V0.75-r1/
  Final Fantasy VI (Korean V0.75-r1).bin
  Final Fantasy VI (Korean V0.75-r1).cue
  patch-result.json
  읽어주세요.txt
```

에뮬레이터에서는 **CUE 파일**을 선택합니다. BIN 이름만 바꾸면 CUE의 참조 이름이 틀어지므로 두 파일은 함께 유지하세요.

### 패처가 검사하는 것

| 단계 | 동작 |
| --- | --- |
| 패처 내부 확인 | xdelta 패치와 변환 EXE의 크기·SHA-256 확인 |
| 원본 확인 | 원본 BIN 크기·SHA-256 확인 |
| 파일 생성 | 선택한 출력 폴더의 전용 임시 디렉터리에서 변환 |
| 결과 확인 | 완성 BIN 크기·SHA-256 확인 |
| 배포 완료 | 검증 성공 시에만 결과 폴더로 이동하고 CUE·검사 기록 제공 |

완성 BIN의 SHA-256:

```text
d3bbb7bd55c4a879f6abeef63845e40972040fc381fd0e316336f04e5fc1c875
```

출력 위치에 `FF6-KR-V0.75-r1`가 이미 있으면 작업을 거부합니다. 다른 출력 폴더를 고르세요. 중간 오류가 나면 이 작업이 만든 임시 폴더만 정리하며 원본과 기존 출력에는 손대지 않습니다. 강제 종료나 정전 때 남은 `.ff6-kr-...` 임시 폴더는 실행할 게임 결과물이 아닙니다.

## 기존 저장 이어하기

1. 기존 메모리 카드 파일을 백업합니다.
2. 에뮬레이터를 종료하거나 현재 게임을 종료하고 새 CUE를 실행합니다.
3. **게임 자체의 불러오기 화면**에서 메모리 카드 저장을 불러옵니다.
4. 새 게임 파일명에 새 카드를 연결하는 설정이라면 기존 카드가 연결되었는지 확인합니다.

예전 개발본의 에뮬레이터 상태 저장을 새 버전에 곧바로 불러오면 이전 RAM·실행 코드·VRAM까지 복원됩니다. 최신 패치가 제대로 적용된 테스트가 되지 않으므로 사용하지 마세요. 패처는 메모리 카드나 상태 저장 파일을 변환하지 않습니다.

## 수동 xdelta 적용

`FF6-KR-V0.75-r1-xdelta.zip`을 풀고 지원 원본 및 xdelta3를 준비합니다. Windows용 xdelta3 3.2.1이 ZIP에 포함되어 있으며 다른 운영체제에서는 해당 환경의 xdelta3를 사용합니다.

```powershell
.\xdelta3.exe -d -s "Final Fantasy VI (Japan).bin" "FF6-KR-V0.75-r1.xdelta" "Final Fantasy VI (Korean V0.75-r1).bin"
Get-FileHash -Algorithm SHA256 "Final Fantasy VI (Korean V0.75-r1).bin"
```

제공된 CUE를 결과 BIN과 같은 폴더에 두세요. 수동 적용에서도 원본과 결과 해시를 확인해야 합니다. `manifest.json`은 원본·결과·패치·변환 도구의 검사 기준입니다.

## 명령줄 자동화

패처 EXE는 GUI 없이 검사·적용할 수도 있습니다. `--output`에는 이미 존재하는 부모 폴더를 지정합니다.

```powershell
.\FF6-KR-Patcher-V0.75-r1.exe --self-check --report "self-check.json"
.\FF6-KR-Patcher-V0.75-r1.exe --source "D:\Games\Final Fantasy VI (Japan).bin" --output "D:\Patched" --report "patch-report.json"
```

GUI 형식 EXE이므로 콘솔 출력 대신 `--report`의 JSON을 확인하세요. 성공은 종료 코드 0과 `status: passed`, 실패는 종료 코드 1과 `status: failed`입니다.

## 오류 메시지

| 메시지 | 확인할 것 |
| --- | --- |
| 원본 크기가 다름 | BIN 대신 CUE/CHD/ZIP을 골랐는지, 지원 덤프인지 확인 |
| 원본이 일치하지 않음 | 다른 판본이나 이미 패치한 파일인지 확인. 파일명을 바꿔도 내용은 바뀌지 않음 |
| 결과 폴더가 이미 있음 | 다른 출력 부모 폴더 선택 |
| 패처 내부 파일 손상 | 릴리스에서 다시 받고 SHA256SUMS 확인 |
| 쓰기 실패/공간 부족 | 쓰기 가능한 로컬 폴더와 충분한 여유 공간 선택 |

배포 EXE에는 코드 서명이 없습니다. 다운로드 파일의 출처와 해시를 확인할 수 있도록 [릴리스](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr/releases/tag/v0.75-r1)에 검사값을 함께 제공합니다.
