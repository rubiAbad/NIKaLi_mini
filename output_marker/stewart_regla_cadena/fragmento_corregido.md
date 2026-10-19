# 3.4 Regla de la cadena

Suponga que se le pide derivar la función

$$F(x) = \sqrt{x^2 + 1}$$

Las fórmulas de derivación que usted aprendió en las secciones anteriores de este capítulo no le permiten calcular $F'(x)$.

Observe que $F$ es una función compuesta. De hecho, si hacemos $y = f(u) = \sqrt{u}$ y $u = g(x) = x^2 + 1$, entonces podemos escribir $y = F(x) = f(g(x))$; es decir, $F = f \circ g$. Sabemos cómo derivar tanto $f$ como $g$, de modo que sería útil contar con una regla que nos indique cómo hallar la derivada de $F = f \circ g$ en términos de las derivadas de $f$ y $g$.

Resulta que la derivada de la función compuesta $f \circ g$ es el producto de las derivadas de $f$ y $g$. Este hecho es uno de los más importantes de las reglas de derivación y se llama **regla de la cadena**. Esto parece verosímil si interpretamos las derivadas como razones de cambio. Consideremos $du/dx$ como la razón de cambio de $u$ respecto a $x$, $dy/du$ como la razón de cambio de $y$ respecto a $u$, y $dy/dx$ como la razón de cambio de $y$ respecto a $x$. Si $u$ cambia al doble de rapidez de $x$ y $y$ varía tres veces más rápido que $u$, entonces parece razonable que $y$ se modifique seis veces más rápido que $x$, y, por tanto, esperamos que

$$\frac{dy}{dx} = \frac{dy}{du} \frac{du}{dx}$$

> **Regla de la cadena:** Si $g$ es derivable en $x$ y $f$ es derivable en $g(x)$, entonces la función compuesta $F = f \circ g$ definida mediante $F(x) = f(g(x))$ es derivable en $x$, y $F'$ está dada por el producto:
> 
> $$F'(x) = f'(g(x)) \cdot g'(x)$$
> 
> En la notación de Leibniz, si $y = f(u)$ y $u = g(x)$ son funciones derivables, entonces:
> 
> $$\frac{dy}{dx} = \frac{dy}{du} \frac{du}{dx}$$

### Comentarios sobre la demostración de la regla de la cadena

Sea $\Delta u$ el cambio en $u$ correspondiente a un cambio de $\Delta x$ en $x$; es decir,

$$\Delta u = g(x + \Delta x) - g(x)$$

Entonces el cambio correspondiente en $y$ es

$$\Delta y = f(u + \Delta u) - f(u)$$

Resulta tentador escribir

$$\frac{dy}{dx} = \lim_{\Delta x \rightarrow 0} \frac{\Delta y}{\Delta x}$$