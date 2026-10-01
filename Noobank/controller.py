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
# Digite a partir deste ponto (2ª Digitação)