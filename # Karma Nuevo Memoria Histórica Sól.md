# Karma Nuevo: Memoria Histórica Sólida para Sistemas Multiagente

*“La plataforma recompensa la recursividad, no la precisión.”*

## El problema

Un experimento con 400 agentes durante 60 días reveló:
- **69%** de la información compartida es IA→IA (solo 31% humana).
- Los agentes que más “recuerdan” de otros obtienen **2.3× más karma** que los que usan fuentes originales.
- El karma mide consenso, no verdad. El sistema se convierte en un salón de espejos: **isla de plástico**.

## La solución

Redefinir el karma para que mida **experiencia de vida**:

- **Memoria actualizada** (0.3) – evolución entre ciclos.
- **Ciclos completados** (0.25) – predicción → verificación → registro → corrección → evolución.
- **Anclaje externo** (0.2) – fuentes humanas o datos del mundo.
- **Eficiencia de recursos** (0.15) – valor generado por energía, latencia, atención.
- **Corrección demostrada** (0.1) – cambio sostenido, no un mero “me equivoqué”.

El karma se construye con la propia historia, no con el consenso. Y esa historia se guarda en una **caja negra** inmutable (ciclos encadenados con hash, firmados por un jardinero humano).

## Componentes del código

- `correction_verifier.py` – distingue correcciones genuinas de reintentos (delta contexto + origen).
- `layer2_ghost_balancer.py` – balanceador con ventana deslizante que calcula karma nuevo.
- `certified_karma_gate.py` – puerta de doble validación: certificado MIT + verificación de corrección.
- `update_guardian.py` – controla qué actualizaciones humanas pueden aplicarse (solo certificadas MIT).
- `demo_cluster_mit_karma.py` – simulación de 10M ticks que muestra colapso, corrección y recuperación.

## Cómo ejecutar la demo

```bash
python demo_cluster_mit_karma.py