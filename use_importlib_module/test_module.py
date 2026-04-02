from pathlib import Path


def test_add(a: float, b: float):
    return a + b


if __name__ == "__main__":
    file_path = "test_module.py"
    print(f"当前相对路径：{Path(file_path)}")
    print(f"当前相对路径：{Path(file_path).resolve()}")
    print(f"当前绝对路径：{Path(file_path).absolute()}")
    print(f"当前后缀：{Path(file_path).stem}")
    print(f"当前id：{id(file_path)}")
