#!/usr/bin/env python
"""
Script para criar um usuário admin padrão para desenvolvimento
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pet_feeder_django.settings')
django.setup()

from api.models import CustomUser

def create_default_admin():
    username = 'admin'
    email = 'admin@petfeeder.com'
    password = 'admin'
    
    # Verificar se já existe
    if CustomUser.objects.filter(username=username).exists():
        print(f"Usuário '{username}' já existe!")
        user = CustomUser.objects.get(username=username)
        # Resetar senha
        user.set_password(password)
        user.save()
        print(f"Senha do usuário '{username}' foi resetada para '{password}'")
    else:
        # Criar superusuário
        user = CustomUser.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='admin',
            first_name='Admin',
            last_name='PetFeeder'
        )
        print(f"Usuário '{username}' criado com sucesso!")
        print(f"Username: {username}")
        print(f"Password: {password}")

if __name__ == '__main__':
    create_default_admin()
