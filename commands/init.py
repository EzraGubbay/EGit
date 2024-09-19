import os, shutil

def execute():
    working = os.getcwd()

    if ".egit" in os.listdir():
        print(f"Reinitializing existing repository in {working}")
        shutil.rmtree(".egit")
        os.remove(".egitignore")
    else:
        print(f"Initializing new repository in {working}")
    os.mkdir(".egit")
    with open(".egitignore", "w") as f:
        pass
