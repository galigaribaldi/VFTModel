# Guía de Contribución — VFT Model

## Flujo de trabajo

```
feature/mi-cambio  →  PR a DEV  →  merge  →  PR de DEV a main  →  merge
```

Nunca se hace push directo a `main` ni a `DEV`. Todo cambio entra via Pull Request.

---

## 1. Preparar el entorno

```bash
git clone https://github.com/galigaribaldi/VFTModel.git
cd VFTModel

python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# source venv/Scripts/activate    # Windows (Git Bash)

make install
cp .env.example .env.local
```

---

## 2. Crear una rama de trabajo

Siempre partir de `DEV` actualizado:

```bash
git checkout DEV
git pull origin DEV
git checkout -b feature/mi-cambio
```

### Convención de nombres de rama

| Prefijo | Cuándo usarlo | Ejemplo |
|---------|--------------|---------|
| `feature/` | Nueva funcionalidad o indicador | `feature/betweenness-centrality` |
| `fix/` | Corrección de bug | `fix/orchestrator-infinite-loop` |
| `docs/` | Solo documentación | `docs/update-contributing` |
| `refactor/` | Reestructuración sin cambio funcional | `refactor/split-routers` |

---

## 3. Convención de commits

Formato: `tipo(scope): descripción en imperativo`

| Tipo | Cuándo usarlo |
|------|--------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Cambios en documentación |
| `refactor` | Refactor sin cambio funcional |
| `test` | Agregar o corregir tests |
| `chore` | Tareas de mantenimiento (deps, config) |

**Ejemplos válidos:**
```
feat(api): add betweenness centrality endpoint
fix(orchestrator): add max_intentos guard to prevent infinite loop
docs(readme): add Docker resource comparison section
refactor(api): split main.py into routers
```

El scope es opcional pero recomendado. La descripción va en minúsculas y sin punto final.

---

## 4. Abrir el Pull Request

```bash
git push origin feature/mi-cambio
```

Luego en GitHub: **New Pull Request** → base: `DEV` ← compare: `feature/mi-cambio`.

Completa la plantilla que aparece automáticamente y verifica el checklist antes de enviar.

### PR de DEV a main

Cuando `DEV` acumule cambios estables, el autor principal abre un PR de `DEV` → `main`. El título debe resumir el conjunto de cambios incluidos.

---

## 5. Correr los tests antes de hacer PR

```bash
make test
```

La suite requiere el servidor activo y apimetro corriendo. Si no tienes apimetro local, usa el entorno DEV:

```bash
make run-dev   # en una terminal
make test      # en otra terminal
```

---

## Estructura del proyecto

```
src/
├── api/            # FastAPI — endpoints, schemas, dependencias
├── core/           # Dominio — algoritmos, modelos, servicios
└── infrastructure/ # Clientes externos — go_client (apimetro)

tests/              # Suite pytest de integración
notebooks/          # Análisis exploratorio (uso local, no publicados)
```

Ver arquitectura completa en el [README](README.md) y la documentación técnica en [GitHub Pages](https://galigaribaldi.github.io/VFTModel).
