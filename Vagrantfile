Vagrant.configure("2") do |config|
    config.vm.box = "completeVagrant/BodhiLinux"
    config.vm.network "forwarded_port", guest: 5005, host: 5005
    config.vm.network "public_network"
    config.vm.provider "virtualbox" do |vb|
        vb.memory = 2048
        vb.cpus = 2
    end
    config.vm.provision "shell", inline: <<-SHELL
        sudo apt install python3 python3-pip -y
        sudo apt install zip -y
        wget https://github.com/RonitKesarkar/SplidApp/archive/refs/heads/vagrant.zip
        unzip vagrant.zip
        cd SplidApp-vagrant/
        pip install -r requirements.txt
        python3 app.py
    SHELL
end