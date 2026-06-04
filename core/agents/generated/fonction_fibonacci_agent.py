def fibonacci(n):
    """
    Calcule la valeur de Fibonacci pour n.

    Args:
    n (int): Le rang du terme de Fibonacci à calculer.

    Returns:
    int: Le n-ième terme de la suite de Fibonacci.
    """
    # Premier et deuxième termes de la suite de Fibonacci
    a, b = 0, 1
    
    # Si n est 0 ou 1, retourne le n-ème terme directement
    if n == 0:
        return a
    elif n == 1:
        return b
    
    # Calcul des termes successifs jusqu'à n
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b

# Test de la fonction fibonacci
print(fibonacci(10))  # Doit retourner 55