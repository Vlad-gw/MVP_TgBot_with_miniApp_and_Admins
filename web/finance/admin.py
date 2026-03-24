from django.contrib import admin
from django.contrib.auth.models import Group, User as DjangoUser

from .models import (
    User,
    Category,
    Transaction,
    Budget,
    AuthCode,
    TransactionTemplate,
)

admin.site.site_header = "Финансовый сервис — админка"
admin.site.site_title = "Админка"
admin.site.index_title = "Панель управления"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "username_display",
        "first_name",
        "created_at",
    )
    search_fields = (
        "telegram_id",
        "username",
        "first_name",
    )
    list_filter = ("created_at",)
    ordering = ("-id",)
    readonly_fields = ("id", "created_at")
    list_per_page = 50

    @admin.display(description="Username")
    def username_display(self, obj):
        return f"@{obj.username}" if obj.username else "—"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "colored_type",
    )
    search_fields = ("name",)
    list_filter = ("type",)
    ordering = ("type", "name")
    readonly_fields = ("id",)
    list_per_page = 50

    @admin.display(description="Тип")
    def colored_type(self, obj):
        return "🟢 Доход" if obj.type == "income" else "🔴 Расход"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "colored_type",
        "amount",
        "category",
        "date",
        "short_note",
    )
    search_fields = (
        "note",
        "user__username",
        "user__first_name",
        "user__telegram_id",
        "category__name",
    )
    list_filter = (
        "type",
        "date",
        "category",
    )
    raw_id_fields = ("user", "category", "suggested_category")
    ordering = ("-date", "-id")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "date"
    list_per_page = 100

    @admin.display(description="Тип")
    def colored_type(self, obj):
        return "🟢 Доход" if obj.type == "income" else "🔴 Расход"

    @admin.display(description="Описание")
    def short_note(self, obj):
        if not obj.note:
            return "—"
        return obj.note[:60] + ("..." if len(obj.note) > 60 else "")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "category",
        "month",
        "limit_amount",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__telegram_id",
        "category__name",
    )
    list_filter = (
        "month",
        "category",
        "created_at",
    )
    raw_id_fields = ("user", "category")
    ordering = ("-month", "-id")
    readonly_fields = ("id", "created_at")
    list_per_page = 50


@admin.register(AuthCode)
class AuthCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "short_code_hash",
        "expires_at",
        "used_at",
        "created_at",
        "is_used",
    )
    search_fields = (
        "telegram_id",
        "code_hash",
    )
    list_filter = (
        "expires_at",
        "used_at",
        "created_at",
    )
    ordering = ("-id",)
    readonly_fields = ("id", "created_at", "used_at", "code_hash")
    list_per_page = 50

    @admin.display(description="Хэш кода")
    def short_code_hash(self, obj):
        if not obj.code_hash:
            return "—"
        return obj.code_hash[:16] + "..."

    @admin.display(boolean=True, description="Использован")
    def is_used(self, obj):
        return obj.used_at is not None


@admin.register(TransactionTemplate)
class TransactionTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "colored_type",
        "amount",
        "category",
        "user",
        "usage_count",
        "last_used_at",
        "created_at",
    )
    search_fields = (
        "name",
        "note",
        "user__username",
        "user__first_name",
        "user__telegram_id",
        "category__name",
    )
    list_filter = (
        "type",
        "created_at",
        "last_used_at",
    )
    raw_id_fields = ("user", "category")
    ordering = ("-id",)
    readonly_fields = ("id", "created_at", "updated_at", "last_used_at")
    list_per_page = 50

    @admin.display(description="Тип")
    def colored_type(self, obj):
        return "🟢 Доход" if obj.type == "income" else "🔴 Расход"


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(DjangoUser)
except admin.sites.NotRegistered:
    pass