# TASK-002: Python 버전 mismatch 해결 및 환경 재설정

## 개요
프로젝트 요구 사항인 Python 3.11+ 버전을 충족하지 못해 발생하는 설치 오류를 해결합니다.

## 작업 목록
- [x] 현재 시스템의 Python 버전 확인
- [x] Python 3.11+ 설치 (필요시)
- [x] 기존 가상 환경(`venv`) 삭제 및 재생성
- [x] 의존성 설치 (`make install`) 확인

## 비고
- 현재 환경: **Python 3.11.14**, **Node.js/npm 설치됨**
- 해결 완료: `PATH`에 `/opt/homebrew/bin`을 추가하여 `make install` 성공
