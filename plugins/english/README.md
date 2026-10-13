# english · /english:phrase

Aprende las frases en inglés que escuchas en reuniones, chats o clases.
Claude te las explica en español y crea tarjetas de Anki (repetición espaciada) automáticamente.

## Qué hace

- `/english:phrase circle back -- lo escuché en una reunión` → explicación + 2 tarjetas:
  **reconocer** (oración en inglés con audio → significado) y **producir** (situación en español → frase en inglés).
- `/english:phrase transcript: <texto>` → elige las 5–8 frases más útiles de una transcripción o chat.
- `/english:phrase review` → resumen semanal, tus tarjetas más difíciles (con reescritura) y un roleplay de 5 minutos.
- `/english:phrase setup` → configura Anki.

No duplica frases (agrega el nuevo contexto), etiqueta por fuente y registro, sincroniza con AnkiWeb
y, si Anki está cerrado, guarda las frases en cola para agregarlas después.

## Requisitos

- [Claude Code](https://claude.com/claude-code) en tu computadora (no funciona en claude.ai web: necesita acceso a Anki local).
- `python3`.
- [Anki](https://apps.ankiweb.net) de escritorio + add-on **AnkiConnect** (código `2055492159`).
- Opcional: AnkiDroid / AnkiMobile en el celular con la misma cuenta de AnkiWeb.

## Instalación paso a paso

1. **Anki**: instálalo desde https://apps.ankiweb.net, ábrelo y entra a tu cuenta de AnkiWeb con el botón **Sincronizar**.
2. **AnkiConnect**: *Herramientas → Complementos → Obtener complementos…* → código `2055492159` → reinicia Anki.
   Comprueba abriendo `http://localhost:8765` en el navegador (debe decir "AnkiConnect").
3. **Plugin** (en Claude Code, con Anki abierto):
   ```
   /plugin marketplace add victand98/claude-tools
   /plugin install english@victor-tools
   ```
   Sal con `/exit` y vuelve a abrir `claude`.
4. **Configurar**: `/english:phrase setup` (crea el mazo `English::Phrases`, el tipo de nota y 10 tarjetas nuevas al día).
5. **FSRS (a mano, una vez)**: en Anki, ⚙ del mazo *English::Phrases* → *Opciones* → sección **FSRS**: actívalo,
   *Retención deseada* = **0.90**. En **Lapsos**, *Acción para sanguijuelas* = **Solo etiquetar**. **Guardar**.
6. **Probar**: `/english:phrase ballpark figure -- reunión de hoy`.

## Rutina recomendada

- Captura frases en el momento (una nota rápida) y pásalas a la skill una vez al día.
- 5–10 frases nuevas por día, 10–15 minutos de repaso diario.
- `/english:phrase review` una vez por semana, y usa 2–3 frases de verdad en tus reuniones.

## Actualizaciones

`/plugin marketplace update victor-tools`, o activa auto-update en `/plugin` → Marketplaces.
