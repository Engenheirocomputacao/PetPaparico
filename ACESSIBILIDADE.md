# Sistema de Acessibilidade - Pet Paparico

## Funcionalidades Implementadas

### 1. Toolbar de Acessibilidade
Localizada na lateral direita da tela, contém:
- **A+**: Aumentar tamanho da fonte (até 150%)
- **A-**: Diminuir tamanho da fonte (até 80%)
- **Reset**: Restaurar tamanho padrão (100%)
- **Contraste**: Alternar modo alto contraste
- **Fechar**: Ocultar toolbar

### 2. Atalhos de Teclado
- `Ctrl + +`: Aumentar fonte
- `Ctrl + -`: Diminuir fonte
- `Ctrl + 0`: Resetar fonte
- `Ctrl + C`: Alternar alto contraste
- `Escape`: Fechar menu de navegação

### 3. VLibras
- Widget de LIBRAS (Língua Brasileira de Sinais) integrado
- Aparece como um avatar traduzindo o conteúdo
- Posicionado no canto inferior direito

### 4. Alto Contraste
- Fundo preto (#000000)
- Texto branco (#ffffff)
- Links em amarelo (#ffff00)
- Hover em ciano (#00ffff)
- Imagens em escala de cinza com contraste aumentado

### 5. Skip Link
- Link "Pular para o conteúdo principal"
- Aparece ao pressionar Tab no início da página
- Permite pular diretamente para o conteúdo

### 6. Atributos ARIA
- `role="main"`: Conteúdo principal
- `role="navigation"`: Navegação
- `role="menubar"`: Menu bar
- `role="menuitem"`: Itens do menu
- `aria-label`: Descrições para leitores de tela
- `aria-expanded`: Estado do menu (aberto/fechado)
- `aria-hidden`: Elementos decorativos
- `aria-live`: Anúncios dinâmicos para leitores de tela

### 7. Gerenciamento de Foco
- Menu móvel: foco vai para o primeiro item ao abrir
- Ao fechar: foco retorna ao elemento anterior
- Navegação por teclado completa

### 8. Persistência
- Preferências salvas no localStorage
- Mantidas entre sessões
- Aplicadas automaticamente ao carregar a página

## Como Usar

### Para Usuários
1. Acesse qualquer página do sistema
2. Use a toolbar lateral para ajustar acessibilidade
3. Ou use os atalhos de teclado
4. VLibras aparece automaticamente

### Para Desenvolvedores
As melhorias de acessibilidade são aplicadas globalmente através do `base.html`.

## Padrões Seguidos
- WCAG 2.1 Nível AA
- WAI-ARIA Authoring Practices
- eMAG (Modelo de Acessibilidade em Governo Eletrônico)
- Lei Brasileira de Inclusão (LBI)

## Testes Recomendados
1. Navegar apenas com teclado (Tab, Enter, Escape)
2. Usar leitores de tela (NVDA, VoiceOver)
3. Testar com zoom do navegador (até 200%)
4. Verificar contraste de cores
5. Testar VLibras
