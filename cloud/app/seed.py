import os
from .auth import user_store


def main():
    user_store.seed_user(os.getenv("SEED_OPERATOR_USERNAME", "operator1"), os.getenv("SEED_OPERATOR_PASSWORD", "operator1-password"), "operator")
    user_store.seed_user(os.getenv("SEED_SUPERVISOR_USERNAME", "supervisor1"), os.getenv("SEED_SUPERVISOR_PASSWORD", "supervisor1-password"), "supervisor")
    print("seeded active operator users")


if __name__ == "__main__":
    main()
