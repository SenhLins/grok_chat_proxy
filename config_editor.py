import json
import os
import hashlib

# 获取项目根目录
project_root = os.path.abspath(os.path.dirname(__file__))

# config.json 文件的路径
config_file_path = os.path.join(project_root, "config.json")

if __name__ == "__main__":
    if not os.path.exists(config_file_path):
        print(f"config.json not found or empty, creating...")
        config = {
            "cookies": [],
            "last_cookie_index": {
                "grok-2": 0,
                "grok-3": 0,
                "grok-3-thinking": 0,
            },
            "temporary_mode": True,
            "password": None,
        }
        print(f"Enter the cookies you got: ")
        config["cookies"].append(input())
    else:
        with open(config_file_path, "r") as f:
            config = json.load(f)
    again = True
    while True:
        if again:
            num = len(config["cookies"])
            print(f"You have {num} cookies in your config.json file.")
        print("----------")
        print(f"1. Add")
        print(f"2. Delete all")
        print(f"3. Toggle temporary mode")
        print(f"4. Set password")
        print(f"5. Save and exit")
        choice = input()
        if choice == "1":
            print(f"Enter the cookies you got: ")
            config["cookies"].append(input())
            again = True
        elif choice == "2":
            config["cookies"] = []
            print(f"Deleted all cookies, enter new cookies:")
            config["cookies"].append(input())
            again = True
        elif choice == "3":
            config["temporary_mode"] = not config["temporary_mode"]
            print(
                f"Temporary mode is now {'on' if config['temporary_mode'] else 'off'}"
            )
            again = False
        elif choice == "4":
            print(f"Enter the password, leave empty to clear:")
            password = input()
            if password:
                config["password"] = hashlib.sha256(password.encode()).hexdigest()
                print(f"Password set.")
            else:
                config.pop("password", None)
                print(f"Password cleared.")
        elif choice == "5":
            with open(config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False)
            break
