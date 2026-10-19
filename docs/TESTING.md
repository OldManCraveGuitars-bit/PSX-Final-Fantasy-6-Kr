# 검증 범위와 결과

공개 **V0.75-r1 = 내부 v085**, 결과 BIN SHA-256:

```text
d3bbb7bd55c4a879f6abeef63845e40972040fc381fd0e316336f04e5fc1c875
```

아래 결과는 검사 종류별 범위입니다. 전체 게임의 모든 장면을 확인했다는 의미가 아닙니다.

## r1 직업 수정 검사

직업 64개의 원래 복사·확장 경로와 캔버스/글꼴 혼합 출력 80개 사례를 검사했습니다. PSX 작은 글꼴은 수정 후 204개 픽셀 사례, 저장창 재사용 테두리는 188개 사례가 통과했습니다. 부록 710번 참조를 실제 문자열로 해석해 모험가를 확인했습니다.

아래 v084 보고서는 변경하지 않은 대사·전투 경로의 이전 검사 기록입니다. 새 직업 관련 결과는 [수정 범위](verification/v085-job-correction.json), [메뉴](verification/v085-menu-ui-fixes-verification.json), [저장 글꼴](verification/v085-psx-font-banks-verification.json), [이미지](verification/v085-image-verification.json)를 참고하세요.

## 배포 패처 검사

배포할 Windows x64 EXE 자체를 명령줄 모드로 실행했습니다.

- 내장 차분과 변환 도구 해시 확인.
- 지원 원본 → 완성 BIN 변환 및 최신 v085와 결과 해시 일치.
- CUE의 파일명과 트랙 형식 일치.
- 기존 출력 폴더 거부 및 그 안의 파일 보존.
- 크기가 다른 파일 거부.
- 크기가 같고 1바이트만 다른 원본도 SHA-256으로 거부.
- 이미 패치된 BIN 재적용 거부.
- 실패 시 완성 폴더 미생성.
- 원본 SHA-256 불변.
- 한글과 공백을 포함한 출력 경로 처리.

[실제 통합 검사 기록](verification/patcher-integration.json). GUI 창을 띄운 뒤 자동 화면 캡처 도구가 시간 초과되어 이번 배포 과정에서는 시각적 창 배치 검증을 완료하지 못했습니다. EXE 변환과 오류 처리 검사는 완료했습니다.

## 게임 데이터·런타임 검사

| 대상 | 범위 | 자료 |
| --- | --- | --- |
| 적 전용 공격명 | MIPS 생성기/소비 경로 384개, 잘린 참조 0개 | [보고서](verification/v084-enemy-attack-verification.json) |
| 실제 엄니 공격 | 나르셰 두 번째 이벤트 전투의 원래 늑대 AI, 공격 후 전투 계속 진행 | [조건](verification/v084-wolf-native-verification.json) |
| 공격명 숫자 | 공격 경로 255개, 숫자 글리프 10개 원본 픽셀 일치 | [보고서](verification/v084-battle-digit-verification.json) |
| 큰 전투 글씨 | Huffman 1,758개, 원래 이름 경로 613개, 동적 이름 342개 | [보고서](verification/v084-battle-big-verification.json) |
| 전투 이름/보상 | 기본 이름 64개, 보상 이름 320개 사례, 미확정 이름 유지 | 위 큰 글씨 보고서 |
| 필드 대사 | 본편 3,084 + 보조 16 = 3,100개 디코드 | [보고서](verification/v084-dialogue-verification.json) |
| PSX 글꼴 뱅크 | 204개 픽셀 비교 사례 | [보고서](verification/v085-psx-font-banks-verification.json) |
| PSX 창/문구 | 메시지 74개, 테두리 재사용 188개, 원래 영문 글리프 106개 | [보고서](verification/v085-psx-ui-verification.json) |
| 작은 글씨 | 클리핑 20개, 태그 라벨 7개, 반각 공백 | [보고서](verification/v084-native-small-verification.json) |
| 이미지 무결성 | 페이로드 17개, 보호 섹터 4,958개, 원본 불변 | [보고서](verification/v085-image-verification.json) |
| 자원 보존 | 폰트·그림·캐시 경로와 이전 창/숫자 수정 유지 | [보고서](verification/v084-resource-preservation.json) |

네이티브 루틴 검사에 통과해도 화면 구성 전체나 게임 흐름의 모든 문제가 배제되는 것은 아닙니다. 큰 글씨 보고서의 `native_gameplay_verification: pending` 같은 필드는 그 보고서 자체의 범위를 나타냅니다. 별도로 실제 플레이를 확인한 늑대 공격·껍질 반격·메뉴 등의 증거와 구별해 읽어 주세요.

## 문장 관리기

v1.13 EXE로 배포 프로젝트를 열어 **7,720개** 항목, 글꼴 로딩, 공백 6/4px, 자막 12×12 설정을 확인했습니다. 정적 검사 오류 0개이며 높이·연속 공백·동적 문자열·가변 수치 주의가 총 157건, 경계 추정 참고가 6,774건입니다.

[자체 검사](verification/text-manager-self-check.json) · [전체 검사 집계](verification/text-manager-audit-summary.json)

## 메뉴 속도 측정

조건: **Mednafen 1.32.1 PSX**, 정상 에뮬레이션 CD 타이밍, 초반 나르셰 필드. 입력 시점부터 화면 밝기가 안정 상태의 99.5%가 되는 시점까지 4프레임 간격으로 관찰했습니다. 코드나 자원을 임의 주입하지 않은 이미지 비교입니다.

| 항목 | 내부 v080 | 내부 v081 | 결과 |
| --- | ---: | ---: | --- |
| 첫 열기 | 3.53초 | 3.27초 | 0.26초 감소 |
| 반복 열기 | 3.13초 | 3.33초 | 0.20초 증가 |
| 반복 닫기 | 5.20초 | 3.80초 | 1.40초 감소, 약 26.9% |
| 반복 왕복 | 8.33초 | 7.13초 | 1.20초 감소, 약 14.4% |

반복 열기는 이전 188/188프레임, 적용 후 200/200프레임, 닫기는 이전 312/312/312프레임, 적용 후 228/228/228프레임이었습니다. 샘플링 간격의 오차가 있으며 숫자는 특정 장면의 관측값입니다. v085에서도 같은 캐시 코드가 유지되지만 전체 장면을 다시 측정한 것은 아닙니다.

[원 측정 JSON](verification/v081-menu-speed-comparison.json)

## 미검증 범위

전체 플레이스루, 모든 캐릭터/장비/스킬/상태이상 조합, 실기, 모든 에뮬레이터와 렌더러 조합은 미검증입니다. 실제 실행 스크린샷에는 기능 검사를 위해 저장 상태나 RAM 조건을 조정한 사례도 있으며, [스크린샷 문서](SCREENSHOTS.md)에 해당 조건을 구분했습니다.
