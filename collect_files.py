#!/usr/bin/env python3
"""
ViZDoom 클라이언트 파일 수집 스크립트
필요한 파일들을 자동으로 찾아 현재 디렉토리로 복사합니다.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def find_files(source_dir, files_to_find):
    """주어진 디렉토리에서 필요한 파일들을 찾습니다."""
    found_files = {}
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file in files_to_find:
                found_files[file] = os.path.join(root, file)

    return found_files


def copy_files(found_files, dest_dir):
    """찾은 파일들을 대상 디렉토리로 복사합니다."""
    os.makedirs(dest_dir, exist_ok=True)

    copied_files = []
    for file_name, file_path in found_files.items():
        try:
            print(f"복사 중: {file_path} -> {os.path.join(dest_dir, file_name)}")
            shutil.copy2(file_path, os.path.join(dest_dir, file_name))
            copied_files.append(file_name)
        except Exception as e:
            print(f"오류: {file_name} 복사 실패 - {str(e)}")

    return copied_files


def main():
    parser = argparse.ArgumentParser(
        description="ViZDoom 클라이언트 파일 수집 스크립트"
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default=".",
        help="파일을 검색할 소스 디렉토리 (기본값: 현재 디렉토리)",
    )
    args = parser.parse_args()

    # 현재 스크립트 위치
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 검색할 파일 목록
    files_to_find = [
        "client.py",
        "utils.py",
        "cig.cfg",
        "cig.wad",
        "mock.wad",
        "_vizdoom.ini",
    ]

    # 소스 디렉토리 설정
    source_dir = args.source
    if not os.path.isdir(source_dir):
        print(f"오류: 소스 디렉토리 {source_dir}가 존재하지 않습니다.")
        return 1

    print(f"검색 경로: {source_dir}")
    print(f"검색할 파일: {', '.join(files_to_find)}")

    # 파일 검색
    found_files = find_files(source_dir, files_to_find)

    # 결과 출력
    print("\n--- 검색 결과 ---")
    for file in files_to_find:
        if file in found_files:
            print(f"✅ {file}: {found_files[file]}")
        else:
            print(f"❌ {file}: 찾지 못함")

    # 찾은 파일이 없으면 종료
    if not found_files:
        print("\n오류: 필요한 파일을 찾지 못했습니다.")
        return 1

    # 파일 복사 여부 확인
    copy_confirm = input("\n찾은 파일을 현재 디렉토리에 복사하시겠습니까? (y/n): ")
    if copy_confirm.lower() != "y":
        print("작업을 취소합니다.")
        return 0

    # 파일 복사
    copied_files = copy_files(found_files, script_dir)

    # 복사 결과 출력
    print("\n--- 복사 완료 ---")
    for file in files_to_find:
        if file in copied_files:
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")

    # 누락된 파일 안내
    missing_files = [f for f in files_to_find if f not in copied_files]
    if missing_files:
        print(
            f"\n주의: {len(missing_files)}개 파일을 복사하지 못했습니다: {', '.join(missing_files)}"
        )
        print("이 파일들은 수동으로 복사해야 합니다.")
    else:
        print("\n모든 파일이 성공적으로 복사되었습니다!")

    print(
        "\n이제 install_client.sh 또는 setup.py를 실행하여 클라이언트를 설치할 수 있습니다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
