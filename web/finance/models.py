from django.db import models


class User(models.Model):
    id = models.AutoField(primary_key=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    username = models.TextField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    api_key = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-id"]

    def __str__(self) -> str:
        if self.username:
            return f"@{self.username}"
        if self.first_name:
            return self.first_name
        if self.telegram_id:
            return str(self.telegram_id)
        return f"User #{self.id}"


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="categories",
        null=True,
        blank=True,
    )
    name = models.TextField()
    type = models.TextField()  # income / expense

    class Meta:
        managed = False
        db_table = "categories"
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["type", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="transactions",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        db_column="category_id",
        related_name="transactions",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField()
    type = models.TextField()  # income / expense
    note = models.TextField(null=True, blank=True)

    suggested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        db_column="suggested_category_id",
        related_name="suggested_transactions",
        null=True,
        blank=True,
    )

    is_category_accepted = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "transactions"
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        category_name = self.category.name if self.category else "Без категории"
        return f"{self.type}: {self.amount} — {category_name} ({self.date:%Y-%m-%d})"


class Budget(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="budgets",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        db_column="category_id",
        related_name="budgets",
    )

    month = models.DateField()
    limit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "budgets"
        verbose_name = "Бюджет"
        verbose_name_plural = "Бюджеты"
        ordering = ["-month", "-id"]

    def __str__(self) -> str:
        category_name = self.category.name if self.category else f"Категория #{self.category_id}"
        return f"{category_name} — {self.limit_amount} ({self.month})"


class AuthCode(models.Model):
    id = models.AutoField(primary_key=True)
    telegram_id = models.BigIntegerField()
    code_hash = models.TextField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "auth_codes"
        verbose_name = "Код авторизации"
        verbose_name_plural = "Коды авторизации"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Код для {self.telegram_id} до {self.expires_at:%Y-%m-%d %H:%M}"


class TransactionTemplate(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="transaction_templates",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        db_column="category_id",
        related_name="transaction_templates",
        null=True,
        blank=True,
    )

    name = models.TextField()
    type = models.TextField()  # income / expense
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    usage_count = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "transaction_templates"
        verbose_name = "Шаблон транзакции"
        verbose_name_plural = "Шаблоны транзакций"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"