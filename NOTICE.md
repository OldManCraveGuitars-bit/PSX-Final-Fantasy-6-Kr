# 권리 및 구성 요소 고지

파이널 판타지 VI의 원본 게임, 이름·캐릭터·영상·음악·그래픽은 각 권리자의 자산입니다. 본 프로젝트는 비공식 한글 패치이며 공식 제품이나 공식 번역으로 표시하지 않습니다. 원본 BIN, BIOS, 게임 실행에 필요한 완성 이미지는 배포하지 않습니다.

번역/코드가 공개되어 있다는 사실만으로 모든 파일에 동일한 오픈소스 라이선스가 적용되는 것은 아닙니다. 별도 표시 없는 프로젝트 코드·번역에 새로운 포괄적 라이선스를 부여하지 않았습니다. 외부 구성 요소는 아래 각 라이선스를 따릅니다.

| 구성 요소 | 출처·라이선스 | 포함 고지 |
| --- | --- | --- |
| Galmuri7 / Galmuri9 | [quiple/Galmuri](https://github.com/quiple/galmuri), Copyright 2019–2025 Lee Minseo, SIL OFL 1.1 | [OFL](licenses/Galmuri-OFL.txt) |
| xdelta3 3.2.1 | [jmacd/xdelta v3.2.1](https://github.com/jmacd/xdelta/tree/v3.2.1), Apache 2.0 | [라이선스](licenses/xdelta-Apache-2.0.txt) |
| BLAKE3 1.8.5 | xdelta3 공식 빌드의 정적 의존성, [BLAKE3-team/BLAKE3](https://github.com/BLAKE3-team/BLAKE3/tree/1.8.5), Apache 2.0 선택 | [라이선스](licenses/BLAKE3-Apache-2.0.txt) |
| liblzma / XZ 5.8.3 | xdelta3 공식 빌드의 정적 의존성, [tukaani-project/xz](https://github.com/tukaani-project/xz/tree/v5.8.3), 0BSD | [고지](licenses/xz-COPYING.txt), [0BSD](licenses/xz-0BSD.txt) |
| Python 3.13 | [Python](https://www.python.org/), PSF 및 포함 구성 요소 | [라이선스](licenses/Python-LICENSE.txt) |
| Tcl/Tk 8.6 | [Tcl/Tk](https://www.tcl-lang.org/), 각 license.terms | [Tcl](licenses/tcl8.6-license.terms), [Tk](licenses/tk8.6-license.terms) |
| PyInstaller | [PyInstaller](https://pyinstaller.org/), 배포 실행 파일에 관한 예외 조항 포함 | [COPYING](licenses/PyInstaller-COPYING.txt) |
| Pillow | 문장 관리기 이미지/글꼴 처리, [Pillow](https://python-pillow.org/) | [라이선스 및 포함 구성 요소](licenses/Pillow-LICENSE) |

배포 EXE는 Python/Tk 런타임을 포함하며, 문장 관리기는 Pillow와 갈무리 글꼴도 포함합니다. 패처와 수동 패치 패키지는 xdelta3의 변경하지 않은 공식 Windows x64 바이너리를 포함합니다. 라이선스 원문은 각 ZIP에도 함께 제공합니다.
