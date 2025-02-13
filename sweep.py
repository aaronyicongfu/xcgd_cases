import argparse

if __name__ == "__main__":

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("case-folder", type=str, help="case folder")
