#!/usr/bin/env python3
"""
Script para criar dados de teste no banco
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pet_feeder_django.settings')
django.setup()

from api.models import CustomUser, Pet, DeviceStatus
from django.utils import timezone

print("🚀 Criando dados de teste...")

# Criar usuário admin se não existir
if not CustomUser.objects.filter(username='admin').exists():
    print("📝 Criando usuário admin...")
    admin = CustomUser.objects.create_user(
        username='admin',
        email='admin@petpaparico.com',
        password='admin123',
        name='Administrador'
    )
    print("✅ Usuário admin criado!")
else:
    admin = CustomUser.objects.get(username='admin')
    print("✅ Usuário admin já existe")

# Criar pet de teste
if not Pet.objects.exists():
    print("📝 Criando pet de teste...")
    pet = Pet.objects.create(
        user=admin,
        name='Rex',
        species='Cachorro',
        breed='Golden Retriever',
        age=3,
        weight=30.5,
        dietaryRestrictions='Nenhuma'
    )
    print(f"✅ Pet '{pet.name}' criado!")
else:
    pet = Pet.objects.first()
    print(f"✅ Pet '{pet.name}' já existe")

# Criar status do dispositivo
DeviceStatus.objects.update_or_create(
    user=admin,
    defaults={
        'isOnline': True,
        'foodLevel': 85,
        'lastSeen': timezone.now()
    }
)
print("✅ Status do dispositivo atualizado!")

print("\n✨ Dados de teste criados com sucesso!")
print(f"\n📋 Informações:")
print(f"   Usuário: admin / admin123")
print(f"   Pet: {pet.name} (ID: {pet.id})")
print(f"   Ração: 85%")
print(f"\n🎮 Acesse o simulador: http://localhost:8000/api/device/simulator/")
