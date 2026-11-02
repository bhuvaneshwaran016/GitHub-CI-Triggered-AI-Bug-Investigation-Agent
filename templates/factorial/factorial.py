def factorial(n):
    if n < 0:
        raise ValueError("Factorial Can't handle negative numbers")
    elif n == 0 or n == 1:
        return 1
    else:
        fact = 1
        for i in range(1, n + 1):
            fact *= i
        return fact


def add(a, b):
    return a + b


def fibonacci(n):
    if n < 0:
        raise ValueError("Fibonacci can't handle negative numbers")
    elif n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
