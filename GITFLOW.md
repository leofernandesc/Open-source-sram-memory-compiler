# Git Flow

## Estrutura de Branches

### Branches Principais
- **main**: Código em produção, sempre estável
- **develop**: Branch de integração para desenvolvimento

### Branches de Suporte

#### Feature Branches
- Nomenclatura: `feature/<nome-da-feature>`
- Origem: `develop`
- Merge para: `develop`
- Exemplo: `feature/sram-layout-generator`

```bash
# Criar feature
git checkout develop
git checkout -b feature/nome-da-feature

# Finalizar feature
git checkout develop
git merge --no-ff feature/nome-da-feature
git branch -d feature/nome-da-feature
```

#### Release Branches
- Nomenclatura: `release/<versao>`
- Origem: `develop`
- Merge para: `main` e `develop`
- Exemplo: `release/1.0.0`

```bash
# Criar release
git checkout develop
git checkout -b release/1.0.0

# Finalizar release
git checkout main
git merge --no-ff release/1.0.0
git tag -a v1.0.0 -m "Release version 1.0.0"

git checkout develop
git merge --no-ff release/1.0.0
git branch -d release/1.0.0
```

#### Hotfix Branches
- Nomenclatura: `hotfix/<versao>`
- Origem: `main`
- Merge para: `main` e `develop`
- Exemplo: `hotfix/1.0.1`

```bash
# Criar hotfix
git checkout main
git checkout -b hotfix/1.0.1

# Finalizar hotfix
git checkout main
git merge --no-ff hotfix/1.0.1
git tag -a v1.0.1 -m "Hotfix version 1.0.1"

git checkout develop
git merge --no-ff hotfix/1.0.1
git branch -d hotfix/1.0.1
```

## Workflow

1. **Desenvolvimento normal**: trabalhe em feature branches
2. **Preparação para release**: crie release branch quando develop estiver pronto
3. **Correções urgentes**: use hotfix branches

## Configuração do Repositório

### Para fazer fork e configurar seu próprio repositório:

```bash
# 1. Faça fork no GitHub do repositório leofernandesc/Open-source-sram-memory-compiler

# 2. Adicione seu fork como remote
git remote rename origin upstream
git remote add origin https://github.com/SEU-USUARIO/Open-source-sram-memory-compiler.git

# 3. Ou use SSH
git remote set-url origin git@github.com:SEU-USUARIO/Open-source-sram-memory-compiler.git

# 4. Push da branch develop
git push -u origin develop
```

### Sincronizar com upstream:

```bash
git fetch upstream
git checkout develop
git merge upstream/develop
```

## Regras

- Nunca commitar direto em `main` ou `develop`
- Sempre usar `--no-ff` nos merges (preserva histórico de branches)
- Tags sempre em `main`
- Release branches permitem apenas bugfixes, sem novas features
