"""
===============================================================================
MODEL — camada de DADOS e REGRAS DE NEGÓCIO (padrão MVC)
===============================================================================
Este é o ÚNICO arquivo de Model do projeto. Ele reúne:

    1) As classes que representam os DADOS do app (Transaction e Contact);
    2) A classe principal do Model — `BankAccount` — que guarda o estado da
       conta (saldo, extrato, contatos) e concentra TODAS as regras de
       negócio (ex.: "não pode transferir valor <= 0", "saldo não pode
       ficar negativo"). Nem a View nem o Controller sabem esses detalhes;
       eles só chamam os métodos que o Model oferece.

O Model NUNCA importa `flet` e NUNCA sabe desenhar nada na tela. Ele só
guarda e manipula dados. Quem desenha é a View; quem decide "quando" chamar
o quê é o Controller.

"""

# ABC e abstractmethod são as ferramentas do Python para criar classes e
# métodos abstratos (paradigma de ABSTRAÇÃO).
from abc import ABC, abstractmethod

# dataclass evita ter que escrever o __init__ "na mão" para classes que só
# guardam dados (Transaction e Contact).
from dataclasses import dataclass

# Usado só para pegar a data atual (dia/mês) de uma nova transação de Pix.
from datetime import datetime


# ------------------------------------------------------------------------
# Classes de DADOS (guardam informação, não têm regra de negócio própria)
# ------------------------------------------------------------------------
@dataclass
class Transaction:
    """Representa UMA transação (entrada ou saída) do extrato."""

    id: str
    description: str
    category: str
    amount: float  # positivo = entrada (dinheiro chegou) | negativo = saída
    date: str
    emoji: str

    @property
    def is_income(self) -> bool:
        """Entrada (True) se o valor for maior ou igual a zero."""
        return self.amount >= 0

@dataclass
class Contact:
    """Representa um contato fictício para quem é possível fazer Pix."""

    name: str
    key_type: str
    key_masked: str
    initial: str
    color: str


def _today_label() -> str:
    """Retorna a data atual no formato 'dia/mês' (ex.: '11/09')."""
    return datetime.now().strftime("%d/%m")

# ------------------------------------------------------------------------
# Classe ABSTRATA: define o "contrato" que toda conta bancária deve seguir
# ------------------------------------------------------------------------
class Account(ABC):
    """
    Classe abstrata (não pode ser instanciada diretamente — tente
    `Account()` e o Python vai recusar).

    Ela existe só para dizer: "toda conta bancária tem que saber transferir
    dinheiro", sem se preocupar em dizer COMO isso é feito. Quem decide o
    "como" é a subclasse concreta (`BankAccount`, logo abaixo).
    """

    @abstractmethod
    def transfer(self, contact_name: str, amount: float) -> Transaction:
        """Efetiva uma transferência e devolve a Transaction criada."""
        raise NotImplementedError

# ------------------------------------------------------------------------
# Classe CONCRETA: o Model principal do app
# ------------------------------------------------------------------------
class BankAccount(Account):
    """
    Model principal do Noobank. Representa a conta do usuário logado:
    reúne saldo, extrato, contatos e o estado de "desbloqueado ou não".

    Guarda também as REGRAS DE NEGÓCIO do app (ex.: valor de transferência
    tem que ser > 0). Assim, tanto a View quanto o Controller podem confiar
    que, se um valor foi aceito aqui, ele é válido.
    """

    def __init__(
        self,
        owner_name: str,
        account_number: str,
        initial_balance: float,
        transactions: list[Transaction],
        contacts: list[Contact],
    ):
        self.owner_name = owner_name
        self.account_number = account_number

        # Atributo "protegido" (o underscore é uma convenção do Python
        # para dizer "não mexa aqui de fora, use a property `balance`").
        # Isso é ENCAPSULAMENTO: o saldo só muda através de regras
        # controladas por este mesmo Model.
        self._balance = initial_balance

        self.balance_hidden = False
        self.unlocked = False

        # list(...) cria uma CÓPIA da lista recebida, para não editar por
        # engano a lista original de dados fictícios (TRANSACTIONS).
        self.transactions: list[Transaction] = list(transactions)
        self.contacts: list[Contact] = contacts

    # --------------------------------------------------------------
    # ENCAPSULAMENTO: acesso controlado ao saldo via property
    # --------------------------------------------------------------
    @property
    def balance(self) -> float:
        """Getter: outros módulos leem `conta.balance`, nunca `_balance`."""
        return self._balance

    @balance.setter
    def balance(self, new_value: float) -> None:
        """
        Setter: toda vez que alguém tenta ALTERAR o saldo (mesmo dentro
        desta própria classe), essa validação roda automaticamente.
        """
        if new_value < 0:
            raise ValueError("O saldo da conta não pode ficar negativo.")
        self._balance = new_value

    def formatted_balance(self) -> str:
        """
        Devolve o saldo (ou "••••••" se estiver oculto) já formatado no
        padrão brasileiro: 1234.5 -> "R$ 1.234,50".
        """
        if self.balance_hidden:
            return "R$ ••••••"
        # Troca "," e "." temporariamente por um marcador "X" para não
        # embaralhar o separador de milhar com o separador decimal.
        texto = f"{self.balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {texto}"

    def toggle_balance_visibility(self) -> None:
        """Alterna entre mostrar e ocultar o saldo na tela Início."""
        self.balance_hidden = not self.balance_hidden

    # --------------------------------------------------------------
    # POLIMORFISMO: esta é a implementação concreta do método abstrato
    # `transfer` declarado lá em cima, na classe `Account`.
    # --------------------------------------------------------------
    def transfer(self, contact_name: str, amount: float) -> Transaction:
        """
        Efetiva uma transferência Pix: valida o valor, cria a Transaction,
        insere no início do extrato e desconta do saldo.
        Lança ValueError se o valor for inválido — quem chama este método
        (o Controller) decide o que fazer com esse erro.
        """
        if amount <= 0:
            raise ValueError("O valor deve ser maior que zero.")

        tx = Transaction(
            id=f"pix-{len(self.transactions) + 1}",
            description=f"Transferência enviada — {contact_name}",
            category="Pix enviado",
            amount=-abs(amount),
            date=_today_label(),
            emoji="↗️",
        )
        # Insere no início da lista: a transação mais recente aparece primeiro.
        self.transactions.insert(0, tx)

        # Usa a property `balance` (não `_balance`) de propósito: assim a
        # validação do setter roda mesmo aqui dentro da própria classe.
        self.balance -= abs(amount)
        return tx

    def recent_transactions(self, limit: int = 4) -> list[Transaction]:
        """As `limit` transações mais recentes, para a tela Início."""
        return self.transactions[:limit]

    def search_transactions(self, text: str, category_filter: str) -> list[Transaction]:
        """
        Filtra o extrato por texto (na descrição ou na categoria) e por
        categoria de filtro: "Todas", "Entradas" ou "Saídas".
        Usado pela tela de Extrato completo.
        """
        texto_busca = text.lower()

        def bate_com_busca(tx: Transaction) -> bool:
            return texto_busca in tx.description.lower() or texto_busca in tx.category.lower()

        resultado = [tx for tx in self.transactions if bate_com_busca(tx)]
        if category_filter == "Entradas":
            return [tx for tx in resultado if tx.is_income]
        if category_filter == "Saídas":
            return [tx for tx in resultado if not tx.is_income]
        return resultado  # "Todas": só considera a busca por texto


# ------------------------------------------------------------------------
# Dados fictícios usados para popular o Model quando o app inicia
# (ficam aqui porque são "dados", não é regra de negócio nem tela).
# ------------------------------------------------------------------------
USER_NAME = "Sabrina C."
ACCOUNT_NUMBER = "Conta 1234-5 • Agência 0001"
INITIAL_BALANCE = 4328.71

INITIAL_TRANSACTIONS: list[Transaction] = [
    Transaction("t1", "Salário", "Renda", 3200.00, "05/09", "💼"),
    Transaction("t2", "Supermercado Vitória", "Mercado", -186.40, "05/09", "🛒"),
    Transaction("t3", "Transferência recebida — Luma Cardoso", "Pix recebido", 150.00, "06/09", "↙️"),
    Transaction("t4", "Serviço de streaming", "Assinatura", -39.90, "07/09", "🎬"),
    Transaction("t5", "Restaurante do Bairro", "Alimentação", -68.00, "08/09", "🍽️"),
    Transaction("t6", "Farmácia Popular", "Saúde", -52.30, "09/09", "💊"),
    Transaction("t7", "Aplicativo de transporte", "Transporte", -24.50, "09/09", "🚕"),
    Transaction("t8", "Loja Online XYZ", "Compras", -215.00, "10/09", "🛍️"),
    Transaction("t9", "Transferência recebida — Aria Ventura", "Pix recebido", 90.00, "10/09", "↙️"),
    Transaction("t10", "Academia Fit Plus", "Assinatura", -99.90, "11/09", "🏋️"),
]

INITIAL_CONTACTS: list[Contact] = [
    Contact("Sabrina Carpenter", "Celular", "(11) 9****-2233", "S", "#8A05BE"),
    Contact("Shakira", "E-mail", "sh****@email.com", "S", "#00A868"),
    Contact("Dua Lipa", "CPF", "123.***.***-09", "D", "#FF7A00"),
    Contact("Ariana Grande", "Chave aleatória", "a1b2***-****", "A", "#2E7DFF"),
    Contact("Pitty", "Celular", "(21) 9****-7788", "A", "#D6249F"),
]


def create_default_account() -> BankAccount:
    """
    'Fábrica' simples que cria a conta inicial do app já populada com os
    dados fictícios acima. Usada pelo main.py para não espalhar esses
    detalhes de inicialização pelo Controller.
    """
    return BankAccount(
        owner_name=USER_NAME,
        account_number=ACCOUNT_NUMBER,
        initial_balance=INITIAL_BALANCE,
        transactions=INITIAL_TRANSACTIONS,
        contacts=INITIAL_CONTACTS,
    )
