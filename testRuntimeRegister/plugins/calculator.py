# plugins/calculator.py
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

async def async_process(data: dict) -> dict:
    # 支持异步函数
    return {"processed": data}