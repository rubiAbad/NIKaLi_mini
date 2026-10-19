# Ejemplo seno compuesto

Nota didáctica de elaboración propia, no transcripción del libro.

Para $y=\sin(x^2)$, la función interna es $g(x)=x^2$ y la externa es $f(u)=\sin(u)$.
La derivada externa respecto de $u$ es $f'(u)=\cos(u)$ y la interna es $g'(x)=2x$.
Al evaluar la derivada externa en $u=g(x)$ y multiplicar por la interna se obtiene
$y'=\cos(x^2)\,2x$. Es importante conservar $x^2$ dentro del coseno.

# Ejemplo potencia compuesta

Nota didáctica de elaboración propia, no transcripción del libro.

Para $y=(3x+1)^4$, la función interna es $g(x)=3x+1$ y la externa es $f(u)=u^4$.
Se tiene $f'(u)=4u^3$ y $g'(x)=3$. Por la regla de la cadena,
$y'=4(3x+1)^3\cdot3=12(3x+1)^3$. Omitir el factor $3$ equivale a olvidar la derivada interna.

# Regla del producto

Nota didáctica de elaboración propia, no transcripción del libro.

Si $y=a(x)b(x)$ y ambas funciones son derivables, entonces
$y'=a'(x)b(x)+a(x)b'(x)$. Por ejemplo, para $y=x\sin(x)$,
$y'=\sin(x)+x\cos(x)$. Un producto de funciones y una composición requieren reglas diferentes.

# Regla del cociente

Nota didáctica de elaboración propia, no transcripción del libro.

Si $y=a(x)/b(x)$, ambas funciones son derivables y $b(x)\ne0$, entonces
$y'=[a'(x)b(x)-a(x)b'(x)]/b(x)^2$.
Para $y=x/(x+1)$, con $x\ne-1$, resulta
$y'=[(x+1)-x]/(x+1)^2=1/(x+1)^2$.
