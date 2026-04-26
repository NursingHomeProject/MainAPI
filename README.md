# Projeto Extensao

Sistema para operacao de casa assistencial, com controle de pacientes, itens, prescricoes, estoque, calculo operacional e alertas internos.

## Estrutura do repositorio

Na raiz do repositorio clonado, use estas pastas:

- `backend`
- `frontend`

## Onboarding rapido no Windows

### 1. Onde clonar

Prefira uma pasta curta:

```powershell
git clone https://github.com/SantLuiz/Projeto_Extensao.git C:\ProjetoExtensao
cd C:\ProjetoExtensao
```

Evite:

- caminhos muito profundos
- ZIP extraido dentro de varias subpastas
- terminal em modo administrador

### 2. Subir o backend

```powershell
cd C:\ProjetoExtensao\backend
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\dev_postgres.ps1 start
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Subir o frontend

```powershell
cd C:\ProjetoExtensao\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### 4. Enderecos

- frontend: `http://127.0.0.1:5173/login`
- backend: `http://127.0.0.1:8000`
- health: `http://127.0.0.1:8000/health`
- swagger: `http://127.0.0.1:8000/docs`

### 5. Login padrao

- e-mail: `admin@casa.local`
- senha: `admin123456`

## Alertas importantes de ambiente

- Use **terminal normal**, nao administrador.
- O backend correto e o da pasta `backend` na raiz do repositorio clonado.
- O frontend correto e o da pasta `frontend` na raiz do repositorio clonado.
- O setup do PostgreSQL local usa runtime fora do repositorio, faz validacao preventiva de caminho longo e tenta fallback automatico quando necessario.

## Guias detalhados

- [COMO TESTAR O PROJETO](./COMO%20TESTAR%20O%20PROJETO.txt)
- [README do backend](./backend/README.md)
