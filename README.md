README — Como rodar o projeto com Vagrant + VMware
🔎 Descrição

Este repositório usa Vagrant com a provider oficial para VMware (Fusion / Workstation) para criar e gerenciar as VMs necessárias ao projeto. O README explica desde os pré-requisitos até comandos comuns e solução de problemas.

✅ Resumo rápido (passos principais)

Instalar Vagrant.

Instalar VMware Fusion (macOS) ou VMware Workstation (Windows/Linux).

Instalar o Vagrant VMware Utility (requisito do provider). 
HashiCorp Developer

Instalar o plugin do Vagrant para VMware: vagrant plugin install vagrant-vmware-desktop. 
GitHub
KitchenCI

Entrar no diretório do projeto e executar: vagrant up (ou vagrant up --provider=vmware_desktop). 
HashiCorp Developer

📋 Pré-requisitos (detalhado)

Vagrant (qualquer versão suportada pelo projeto; verifique com vagrant --version).

VMware Fusion (macOS) ou VMware Workstation (Windows/Linux) — devidamente instalado e licenciado.

Vagrant VMware Utility (serviço/utility que o plugin usa). A instalação do utilitário é necessária para que o plugin funcione corretamente. 
HashiCorp Developer

No macOS o utilitário pode ser instalado via Homebrew Cask: brew install --cask vagrant-vmware-utility. 
Homebrew Formulae

Plugin Vagrant para VMware Desktop: vagrant-vmware-desktop. Instale com vagrant plugin install vagrant-vmware-desktop. 
GitHub
KitchenCI

🛠️ Instalação por sistema operacional (exemplos)
macOS (recomendado com Homebrew)
# Instalar Vagrant (exemplo via Homebrew)
brew tap hashicorp/tap
brew install hashicorp/tap/hashicorp-vagrant

# Instalar o utilitário VMware (necessário)
brew install --cask vagrant-vmware-utility

# Instalar o plugin do Vagrant para VMware Desktop
vagrant plugin install vagrant-vmware-desktop

# Verificar
vagrant --version
vagrant plugin list


(Obs.: abra o VMware Fusion pelo menos uma vez após a instalação e antes de usar vagrant up.)

Ubuntu / Debian (exemplo)
# Instale o Vagrant via pacote oficial (ou apt se disponível)
# Baixe o instalador do Vagrant VMware Utility no site da HashiCorp (releases) e então:
sudo apt install ./vagrant-vmware-utility_<versao>_amd64.deb

# Instale o plugin
vagrant plugin install vagrant-vmware-desktop

# Verifique
vagrant --version
vagrant plugin list


(Para o utilitário, baixe o .deb apropriado da página de releases do Vagrant VMware Utility.) 
HashiCorp Developer

Windows

Instale o Vagrant via instalador oficial (.msi) do site do Vagrant.

Instale o VMware Workstation (executável/instalador oficial).

Faça o download/instalação do Vagrant VMware Utility para Windows (instalador oficial / instruções no site da HashiCorp). 
HashiCorp Developer

Abra PowerShell/CMD como Administrador e rode:

vagrant plugin install vagrant-vmware-desktop
vagrant --version
vagrant plugin list

📁 Preparar e rodar o projeto

No diretório raiz do projeto (onde está o Vagrantfile):

# entrar no diretório do projeto
cd /caminho/para/o/projeto

# subir as VMs (usa o provider configurado no Vagrantfile; opcionalmente force o provider)
vagrant up --provider=vmware_desktop

# checar status
vagrant status


Se o Vagrantfile não definir explicitamente o provider, você pode forçar com --provider=vmware_desktop. O provider atual é vmware_desktop (compatível com Fusion/Workstation) e pode ser usado no Vagrantfile como abaixo. 
HashiCorp Developer

Exemplo mínimo de Vagrantfile
Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"    # ajuste conforme a box do projeto
  config.vm.provider "vmware_desktop" do |v|
    v.gui = false
    # outras opções específicas do provider podem ser adicionadas aqui
  end
end

⌨️ Comandos úteis
vagrant up                        # sobe a VM (use --provider=vmware_desktop se precisar forçar)
vagrant status                    # lista o status das VMs
vagrant ssh                       # conecta via SSH (se o box suportar)
vagrant halt                      # desliga a VM
vagrant reload --provision        # reinicia e reprovisiona
vagrant destroy -f                # destrói a VM (use com cuidado)
vagrant plugin list               # lista plugins instalados
vagrant plugin install <plugin>   # instala plugin
vagrant up --debug                # log detalhado para depuração

🩺 Solução de problemas (quick fixes)

O plugin não instala / erros de dependência: tente primeiro vagrant plugin repair. Se continuar, execute vagrant plugin expunge --reinstall (remove e tenta reinstalar plugins). Em muitos casos isso resolve conflitos após atualizações do Vagrant. 
HashiCorp Developer
GitHub

Erro de comunicação com o utilitário: verifique se o Vagrant VMware Utility está instalado e se o VMware (Fusion/Workstation) foi aberto ao menos uma vez. O utilitário executa um serviço que precisa conseguir comunicar com o VMware. 
HashiCorp Developer

Problemas em Apple Silicon (M1/M2): use boxes compatíveis com arm64 e versões recentes do VMware Fusion que suportem Apple Silicon. Nem todas as boxes x86_64 funcionarão.

Logs de depuração: rode vagrant up --debug e analise a saída; frequentemente indica exatamente qual etapa falhou.

Se o vagrant status mostra a VM criada, mas o VMware não abre: confirme permissões do sistema (macOS Security & Privacy para permitir o VMware acessar eventos ou múltiplos recursos) e que a versão do VMware seja compatível com seu SO.

📌 Dicas finais

Use vagrant plugin list para confirmar que vagrant-vmware-desktop aparece. 
GitHub

Se estiver compartilhando o projeto, inclua instruções de versão mínima do Vagrant/VMware no README (ex.: "Recomendado: Vagrant >= 2.x, VMware Fusion >= 12, Vagrant VMware Utility >= 1.x").

Sempre verifique se há boxes compatíveis com o provider VMware (algumas boxes são otimizadas para VirtualBox).

📝 Licença / Contato

Incluir aqui a licença do projeto (ex.: MIT, Apache-2.0 etc.)

Para dúvidas: adicione seu e-mail ou link do repositório.

Referências (fontes consultadas)

Documentação oficial — instalação do provider VMware (HashiCorp). 
HashiCorp Developer

Vagrant VMware Utility — instalação e uso. 
HashiCorp Developer

Provider/Config (vmware_desktop) — ex.: como configurar no Vagrantfile. 
HashiCorp Developer

Homebrew cask para vagrant-vmware-utility. 
Homebrew Formulae

Repositório oficial vagrant-vmware-desktop (HashiCorp). 
GitHub
