# V0.75 — PSX 파이널 판타지 VI 한글 패치

최신 내부 개발본 **v084**를 정리한 공개 테스트 버전입니다. 과거 내부 v075로 되돌린 배포가 아닙니다.

## 받으실 파일

- **일반 사용자:** `FF6-KR-Patcher-V0.75.zip` — Windows x64 한글 패처 EXE. Python 설치 없이 실행합니다.
- **수동 적용:** `FF6-KR-V0.75-xdelta.zip` — 차분 패치, xdelta3, 매니페스트, CUE 견본.
- **번역 편집:** `FF6-Korean-Text-Manager-V1.13-V0.75.zip` — 독립 실행 문장 관리기와 7,720개 항목.
- `SHA256SUMS.txt` — 배포 ZIP 검사값.

원본 게임과 BIOS는 포함하지 않습니다. GitHub의 자동 `Source code` ZIP 대신 목적에 맞는 위 파일을 받으세요.

## 적용

패처 EXE 실행 → 일본판 원본 BIN 선택 → 출력 폴더 선택 → 적용 완료 → 새 폴더의 CUE 실행.

지원 원본은 **SLPM-86198**, **325,133,424 bytes**입니다. 원본·내장 패치·변환 도구·완성 BIN을 검사하며 원본과 기존 출력 폴더를 덮어쓰지 않습니다.

```text
원본 SHA-256
a607011d9c9442797ae155228e86e9dae6e503aaeb7dc9603ac552ffd8d036df

결과 SHA-256
6bb23a184380ce6c158185d4c634b4b0ca23a3196f16da47be2b40afd33b9454
```

구버전 상태 저장 대신 새 CUE로 재시작한 뒤 게임 내 메모리 카드 저장을 불러오세요. 카드 파일은 먼저 백업하고 새 파일명에 올바른 카드가 연결되는지 확인하세요.

## 포함 기능

- 본편·메뉴·전투·PSX 저장 화면·부록 한글화.
- 큰 글씨 원래 크기, 갈무리7 작은 글씨, 반각 공백, 프롤로그 가운데 정렬.
- 패드로 자음/모음을 조합하는 최대 6글자 한글 이름 작성기.
- 원본 영상을 보존한 별도 12×12 오프닝/엔딩 자막, 총 29개 큐.
- 설정 → SELECT 부스트: 인카운트 차단/경험치×5/GIL×5/AP×5, 모두 기본 OFF.
- 원판 부록 해금 조건 유지.
- 일부 필드 자원 캐시로 반복 메뉴 닫기 단축. 초반 실측 5.20 → 3.80초, 전체 왕복 8.33 → 7.13초. 반복 열기는 3.13 → 3.33초로 개선되지 않았습니다.
- 문장 관리기의 폭·줄 수·간격·제어 코드 검사와 저장 전 자동 백업.

## 최근 수정

- 엄니가 니만 나오던 등 적 전용 이름 참조 잘림 수정. 384개 경로 검사.
- 1만 볼트·100만 볼트 등 숫자 글리프 충돌 수정.
- 전투 대사/상태창 처리 복원, 저장 문구와 임시 저장창 테두리 등의 수정 포함.
- 록의 호칭을 트레저 헌터로 통일하고 조사 수정.
- 이름 확정 전 주인공의 ?????? 표시 유지.

## 남은 항목

오페라 노래 가사 자막은 미완료이며 일부 정적 일본어 문구와 판독 불가 갤러리 메모가 남았습니다. 전체 플레이스루·실기·모든 에뮬레이터 조합 검증은 완료되지 않았습니다. 문장 관리기 정적 오류 0개와 실제 게임 전체 무결성은 별개이며 참고/주의 항목이 남아 있습니다.

[저장소 및 18장 스크린샷](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr) · [적용 방법](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr/blob/main/docs/INSTALL.md) · [기능 상세](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr/blob/main/docs/FEATURES.md) · [검증 결과](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr/blob/main/docs/TESTING.md) · [남은 작업](https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr/blob/main/docs/KNOWN_ISSUES.md)
