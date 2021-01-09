def chunk(data: list, n: int):
    return [data[x:x + n] for x in range(0, len(data), n)]
