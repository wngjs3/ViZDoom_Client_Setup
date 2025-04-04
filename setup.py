import os
import sys
import shutil
import subprocess
import platform

print("===== ViZDoom 클라이언트 Python 설치 스크립트 =====")
print("이 스크립트는 ViZDoom 클라이언트에 필요한 Python 패키지를 설치합니다.")

# 현재 디렉토리 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(SCRIPT_DIR, "ViZDoom", "client")

# 디렉토리 생성
os.makedirs(CLIENT_DIR, exist_ok=True)

# 시스템 확인
IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"


def install_requirements():
    """필요한 Python 패키지 설치"""
    print("\n===== Python 패키지 설치 중 =====")

    try:
        # pip 업그레이드
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
        )

        # 필수 패키지 설치
        requirements = [
            "numpy",
            "opencv-python",
            "matplotlib",
            "vizdoom",
            "pillow",
            "requests",
        ]

        for pkg in requirements:
            print(f"설치 중: {pkg}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

        print("모든 Python 패키지가 성공적으로 설치되었습니다!")
        return True
    except Exception as e:
        print(f"패키지 설치 중 오류 발생: {e}")
        return False


def copy_client_files():
    """필요한 클라이언트 파일 복사"""
    print("\n===== 클라이언트 파일 복사 중 =====")

    # 현재 디렉토리의 필요한 파일들 복사
    client_files = [
        "client.py",
        "utils.py",
        "cig.cfg",
        "cig.wad",
        "mock.wad",
        "_vizdoom.ini",
    ]

    for file in client_files:
        src_path = os.path.join(SCRIPT_DIR, file)
        dst_path = os.path.join(CLIENT_DIR, file)

        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"복사 완료: {file}")
        else:
            print(f"경고: {file} 파일을 찾을 수 없습니다")

    # 실행 가능하게 설정
    client_script = os.path.join(CLIENT_DIR, "client.py")
    if os.path.exists(client_script):
        os.chmod(client_script, 0o755)  # 실행 권한 추가


def run_client():
    """클라이언트 실행"""
    print("\n===== ViZDoom 클라이언트 실행 =====")

    client_script = os.path.join(CLIENT_DIR, "client.py")
    if os.path.exists(client_script):
        os.chdir(CLIENT_DIR)
        try:
            subprocess.call([sys.executable, client_script])
        except Exception as e:
            print(f"클라이언트 실행 중 오류 발생: {e}")
    else:
        print(f"오류: {client_script} 파일을 찾을 수 없습니다")


def main():
    """메인 실행 함수"""
    # 시스템 정보 출력
    print(f"운영체제: {platform.system()} {platform.release()}")
    print(f"Python 버전: {platform.python_version()}")

    # macOS 관련 정보
    if IS_MACOS:
        print("\n===== macOS 환경 감지됨 =====")
        print("ViZDoom이 제대로 작동하려면 Homebrew로 다음 패키지를 설치해야 합니다:")
        print("  brew install cmake boost sdl2 wget")

        response = input("Homebrew로 필요한 패키지를 설치하시겠습니까? (y/n): ")
        if response.lower() == "y":
            try:
                # Homebrew 설치 확인
                brew_exists = (
                    subprocess.call(["which", "brew"], stdout=subprocess.DEVNULL) == 0
                )

                if not brew_exists:
                    print("Homebrew가 설치되어 있지 않습니다. 설치를 진행합니다...")
                    subprocess.call(
                        [
                            "/bin/bash",
                            "-c",
                            "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
                        ]
                    )

                # 필수 패키지 설치
                subprocess.call(["brew", "install", "cmake", "boost", "sdl2", "wget"])
            except Exception as e:
                print(f"Homebrew 패키지 설치 중 오류 발생: {e}")

    # Python 패키지 설치
    if not install_requirements():
        print("Python 패키지 설치에 실패했습니다. 설치를 중단합니다.")
        return

    # 클라이언트 파일 복사
    copy_client_files()

    print("\n===== 설치 완료! =====")
    print(f"클라이언트가 다음 경로에 설치되었습니다: {CLIENT_DIR}")
    print("클라이언트를 실행하려면 다음 명령어를 입력하세요:")
    print(f"cd {CLIENT_DIR} && python client.py")

    # 실행 옵션 제공
    response = input("\n지금 클라이언트를 실행하시겠습니까? (y/n): ")
    if response.lower() == "y":
        run_client()


if __name__ == "__main__":
    main()
