from src.bot import OKBot

def main():
    print("Initializing OK Cashbag Auto Clicker...")
    try:
        bot = OKBot()
        # 인자 없이 호출 (무한 루프 모드)
        bot.run()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()

