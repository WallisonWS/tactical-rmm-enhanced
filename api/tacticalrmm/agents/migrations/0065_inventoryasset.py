from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0024_alter_deployment_goarch"),
        ("agents", "0064_filetransfersession_extract"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryAsset",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("ativo_monitorado", "Ativo Monitorado (Com Agente)"),
                            (
                                "ativo_rede",
                                "Ativo de Rede (Switch / Roteador / AP / Firewall)",
                            ),
                            (
                                "passivo_rede",
                                "Passivo de Rede (Patch Panel / Rack / Cabo / Tomada)",
                            ),
                            (
                                "estacao_sem_agente",
                                "Computador / Servidor (Sem Agente)",
                            ),
                            ("equipamento_medico", "Equipamento Médico / Diagnose"),
                            (
                                "impressora_periferico",
                                "Impressora / Scanner / CFTV / Periférico",
                            ),
                        ],
                        db_index=True,
                        default="ativo_rede",
                        max_length=40,
                    ),
                ),
                (
                    "asset_subtype",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                (
                    "patrimonio",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=100
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=255)),
                (
                    "ip_address",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=255
                    ),
                ),
                (
                    "mac_address",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                (
                    "manufacturer",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "model_name",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "serial_number",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "operating_system",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "sector_location",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "responsible",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "status",
                    models.CharField(blank=True, default="ativo", max_length=64),
                ),
                (
                    "source",
                    models.CharField(blank=True, default="manual", max_length=64),
                ),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "imported_by",
                    models.CharField(blank=True, default="", max_length=150),
                ),
                ("extra_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agent",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="inventory_record",
                        to="agents.agent",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_assets",
                        to="clients.site",
                    ),
                ),
            ],
            options={
                "ordering": ("site__client__name", "site__name", "name"),
            },
        ),
    ]
