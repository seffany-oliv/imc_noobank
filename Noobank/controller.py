"""
===============================================================================
CONTROLLER — camada que ORQUESTRA o Model e a View (padrão MVC)
===============================================================================
Este é o ÚNICO arquivo de Controller do projeto: a classe `NoobankController`.

O Controller é o "meio de campo" do MVC:
    • recebe as ações do usuário que vêm da View (clique em um botão,
      texto digitado, navegação entre telas);
    • decide o que fazer: chama métodos do MODEL para ler/alterar dados
      (ex.: `model.transfer(...)`);
    • manda a VIEW se redesenhar com o resultado.

Repare que o Controller NUNCA desenha widgets do Flet diretamente (quem
faz isso é a View) e NUNCA guarda regra de negócio (quem faz isso é o
Model). Ele só "liga os fios".

"""
import asyncio
import flet as ft

from view import HomeView, LockView, PixView, StatementView

class NoobankController:
    """Único Controller do app: conhece o Model e todas as Views."""

    def __init__(self, model):
        self.model = model
        self.page: ft.Page | None = None

    # --------------------------------------------------------------
    # Ponto de entrada: liga o Controller a uma página do Flet
    # --------------------------------------------------------------
    def run(self, page: ft.Page) -> None:
        """Configura a página e liga o sistema de rotas."""
        self.page = page
        page.title = "Noobank — exercício de clone de app bancário"
        page.theme_mode = ft.ThemeMode.LIGHT

        # Define o tamanho da janela (só tem efeito rodando como app
        # desktop; simula as proporções de um celular).
        page.window.width = 320
        page.window.height = 600

        page.on_route_change = self.route_change
        page.on_view_pop = self.view_pop
        self.route_change()  # desenha a tela inicial ("/") assim que o app abre

    # --------------------------------------------------------------
    # Roteamento: decide qual View instanciar para cada rota
    # --------------------------------------------------------------
    def route_change(self, e=None) -> None:
        """
        Chamado toda vez que `page.route` muda. Sempre limpa a pilha de
        Views e recria do zero a tela correspondente à rota atual — por
        isso cada tela "interna" tem seu próprio botão de voltar explícito
        (não existe voltar automático nesse padrão).
        """
        page = self.page
        page.views.clear()

        if page.route == "/home":
            page.views.append(HomeView().build(self) if self.model.unlocked else LockView().build(self))
        elif page.route == "/pix":
            # Proteção: só entra no Pix se já tiver desbloqueado o app antes.
            page.views.append(PixView().build(self) if self.model.unlocked else LockView().build(self))
        elif page.route == "/statement":
            page.views.append(
                StatementView().build(self) if self.model.unlocked else LockView().build(self)
            )
        else:
            # Qualquer outra rota (incluindo "/") cai na tela de bloqueio.
            page.views.append(LockView().build(self))

        page.update()

    async def view_pop(self, e: ft.ViewPopEvent) -> None:
        """
        Executado quando o usuário aciona o 'voltar' nativo do dispositivo.
        Mantido por segurança, embora o fluxo principal use os botões de
        voltar explícitos nos AppBars.
        """
        if e.view is not None and len(self.page.views) > 1:
            self.page.views.remove(e.view)
            await self.page.push_route(self.page.views[-1].route)

    def navigate(self, route: str) -> None:
        """Atalho usado pelas Views para trocar de tela."""
        self.page.navigate(route)

    # --------------------------------------------------------------
    # Ação: autenticação biométrica (SIMULADA) e desbloqueio do app
    # --------------------------------------------------------------
    async def device_authenticate(self, reason: str) -> tuple[bool, str]:
        """
        Autenticação biométrica — SIMULADA.

        Por que não é real no Android: hoje (set/2026) não existe nenhuma
        forma de acessar o leitor de digital/rosto do Android a partir de
        Python puro no Flet:
          - `flet-local-auth` (a extensão oficial) é só um placeholder no
            PyPI, sem nenhuma funcionalidade ainda:
            https://pypi.org/project/flet-local-auth/
        """
        # Delay artificial só para simular o tempo real de leitura da digital.
        await asyncio.sleep(1.0)
        # SEMPRE retorna sucesso — é só uma simulação, nunca falha de verdade.
        return True, "⚠️ Simulado"

    async def unlock(self, status_control: ft.Text) -> None:
        """
        Executa o fluxo completo de desbloqueio, chamado pela LockView ao
        tocar no ícone de digital ou no botão 'Desbloquear'.
        """
        status_control.value = "🔎 Verificando digital..."
        self.page.update()

        ok, message = await self.device_authenticate("Desbloqueie o Noobank para continuar")
        status_control.value = message
        self.page.update()

        if ok:
            # Dá um tempinho para o usuário ler a mensagem de sucesso antes
            # de trocar de tela.
            await asyncio.sleep(0.5)
            self.model.unlocked = True  # libera o acesso às telas internas
            await self.page.push_route("/home")

    # --------------------------------------------------------------
    # Ações da tela Início
    # --------------------------------------------------------------
    def toggle_balance_visibility(self) -> None:
        """Pede ao Model para alternar a visibilidade do saldo."""
        self.model.toggle_balance_visibility()

    # --------------------------------------------------------------
    # Ações da tela Pix
    # --------------------------------------------------------------
    def confirm_pix(self, pix_view: PixView, amount_field: ft.TextField) -> bool:
        """
        Valida e efetiva a transferência a pedido da PixView. Toda a REGRA
        de negócio (valor > 0, etc.) mora no Model — aqui só traduzimos o
        texto digitado, chamamos o Model e tratamos o resultado.
        Devolve True se a transferência foi efetivada, False se houve erro
        de validação (e já deixa a mensagem certa em `amount_field.error_text`).
        """
        # Aceita tanto "10.50" quanto "10,50" como valor válido.
        texto = (amount_field.value or "0").replace(",", ".")
        try:
            valor = float(texto)
        except ValueError:
            amount_field.error_text = "Digite um valor válido"
            self.page.update()
            return False

        try:
            self.model.transfer(pix_view.contact.name, valor)
        except ValueError as erro:
            # Mensagem de erro vem pronta do Model (ex.: "O valor deve
            # ser maior que zero.").
            amount_field.error_text = str(erro)
            self.page.update()
            return False

        pix_view.go_to_success(self)
        return True


