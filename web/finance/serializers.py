from rest_framework import serializers

from .models import Budget, Category, Transaction, TransactionTemplate


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "type",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    suggested_category = CategorySerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    suggested_category_name = serializers.CharField(
        source="suggested_category.name",
        read_only=True,
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "amount",
            "date",
            "note",
            "is_category_accepted",
            "category",
            "category_name",
            "suggested_category",
            "suggested_category_name",
        ]


class BudgetSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id",
            "month",
            "limit_amount",
            "category",
            "category_name",
            "created_at",
        ]


class TransactionTemplateSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = TransactionTemplate
        fields = [
            "id",
            "name",
            "type",
            "amount",
            "note",
            "category",
            "category_name",
            "usage_count",
            "created_at",
            "updated_at",
            "last_used_at",
        ]
