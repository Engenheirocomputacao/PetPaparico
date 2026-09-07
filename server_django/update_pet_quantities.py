#!/usr/bin/env python3
"""
Script para atualizar a quantidade padrão dos pets
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pet_feeder_django.settings')
django.setup()

from api.models import Pet

print("🔄 Atualizando quantidades padrão dos pets...")

# Definir quantidades por nome do pet
quantities = {
    'Koriane': 50,
    'Bolt': 150,
    'Dog': 100,
}

# Atualizar pets existentes
for pet_name, quantity in quantities.items():
    pets = Pet.objects.filter(name=pet_name)
    if pets.exists():
        for pet in pets:
            pet.defaultQuantity = quantity
            pet.save()
            print(f"✅ {pet.name}: {quantity}g")
    else:
        print(f"⚠️  Pet '{pet_name}' não encontrado")

print("\n✨ Quantidades atualizadas com sucesso!")
print("\n📋 Resumo:")
for pet in Pet.objects.all():
    print(f"   {pet.name}: {pet.defaultQuantity}g")
