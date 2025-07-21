import time
import discord
from discord.ui import View, Button, Modal, TextInput
from src.database import get_settings, save_application, remove_application, save_settings, init_owners, owners_cache, add_member_to_capt, get_capt, remove_capt, remove_member_from_capt
from src.permissions import check_approver
from src.utils import application_state_manager

start_time = time.time()

class BaseModal(Modal):
    def __init__(self, title: str):
        super().__init__(title=title)
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str):
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


class BaseView(View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
    
    async def handle_error(self, interaction: discord.Interaction, error_message: str):
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)


class ApplicationReviewer:
    def __init__(self, application_view):
        self.application_view = application_view
    
    def is_being_reviewed(self, message_id: str, user_id: int) -> tuple[bool, str]:
        current_reviewer = application_state_manager.get_state(message_id)
        if current_reviewer and current_reviewer[0] is not None and current_reviewer[0] != user_id:
            return True, current_reviewer[0]
        return False, None
    
    def set_reviewer(self, message_id: str, user_id: int):
        application_state_manager.add_state(message_id, user_id)
    
    def clear_reviewer(self, message_id: str):
        application_state_manager.remove_state(message_id)


class NotificationSender:
    def __init__(self, bot):
        self.bot = bot
    
    async def send_approval_notification(self, applicant_id: str) -> bool:
        try:
            applicant = await self.bot.fetch_user(int(applicant_id))
            await applicant.send("✅ Твою заявку в семью CHILI приняли!")
            return True
        except Exception:
            return False
    
    async def send_denial_notification(self, applicant_id: str, reason: str) -> bool:
        try:
            applicant = await self.bot.fetch_user(int(applicant_id))
            await applicant.send(f"❌ К сожалению, твою заявку в семью CHILI отклонили.\nПричина: `{reason}`")
            return True
        except Exception:
            return False


class RoleManager:
    @staticmethod
    async def assign_approved_role(guild, applicant_id: str) -> bool:
        try:
            _, _, _, approved_role_id = get_settings(guild.id)
            if approved_role_id:
                role = guild.get_role(int(approved_role_id))
                if role:
                    member = guild.get_member(int(applicant_id))
                    if member:
                        await member.add_roles(role)
                        return True
            return False
        except Exception:
            return False


class EmbedBuilder:
    @staticmethod
    def create_application_embed(user: discord.User, form_data: dict) -> discord.Embed:
        embed = discord.Embed(title="Новая заявка в семью", color=discord.Color.red())
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        embed.add_field(name="1. Имя", value=form_data['name'], inline=False)
        embed.add_field(name="2. Возраст", value=form_data['age'], inline=False)
        embed.add_field(name="3. В каких семьях играл", value=form_data['families'], inline=False)
        embed.add_field(name="4. Любимое занятие", value=form_data['favorite'], inline=False)
        embed.add_field(name="5. Ожидание от семьи", value=form_data['expectations'], inline=False)
        embed.set_footer(text=f"ID Отправителя: ({user.id})")
        return embed
    
    @staticmethod
    def create_form_embed(title: str, description: str, color_hex: str = None, image_url: str = None) -> discord.Embed:
        description_with_ansi = f"```ansi\n{description}\n```"
        color = discord.Color.red()
        
        if color_hex:
            hex_color = color_hex.strip()
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            if len(hex_color) == 6 and all(c in '0123456789ABCDEFabcdef' for c in hex_color):
                color = discord.Color(int(hex_color, 16))

        embed = discord.Embed(title=title, description=description_with_ansi, color=color)

        if image_url:
            embed.set_image(url=image_url)
        
        return embed

    @staticmethod
    def create_capt_embed(current_count: int, max_members: int, members_list: str) -> discord.Embed:
        if current_count == max_members:
            color = 0x2ed573
            title_emoji = "✅"
            status = "**ГРУППА СФОРМИРОВАНА!**"
        elif current_count >= max_members * 0.7:
            color = 0xff9f43
            title_emoji = "📋"
            status = "Почти заполнена"
        else:
            color = 0x3742fa
            title_emoji = "📋"
            status = "Набор участников"
        
        embed = discord.Embed(
            title=f"{title_emoji} Группа · {status}",
            color=color
        )
        
        embed.add_field(
            name=f"👥 Участники ({current_count}/{max_members})",
            value=members_list,
            inline=False
        )
        
        progress = "🟩" * current_count + "⬜" * (max_members - current_count)
        embed.add_field(
            name="📊 Прогресс заполнения",
            value=f"`{progress}` {current_count}/{max_members}",
            inline=False
        )
        
        if current_count < max_members:
            embed.set_footer(text="💡 Нажмите кнопку ниже, чтобы присоединиться или покинуть группу")
        
        return embed

    @staticmethod
    def create_final_capt_embed(max_members: int, members_list: str) -> discord.Embed:
        embed = discord.Embed(
            title="🎊 Группа успешно сформирована!",
            description=f"**{max_members}** участников готовы к действию!",
            color=0x2ed573
        )
        
        embed.add_field(
            name="Состав команды:",
            value=members_list,
            inline=False
        )
        
        embed.set_footer(text="Удачи на мероприятии! 🍀")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/881894397288914974.png")
        
        return embed


class CaptMemberValidator:
    def __init__(self, max_members: int):
        self.max_members = max_members
    
    def can_join(self, capt_info: dict, user_id: int) -> tuple[bool, str]:
        current_count = len(capt_info['current_members'])
        
        if current_count >= self.max_members:
            return False, "⚠️ Группа заполнена"
        
        if str(user_id) in capt_info['current_members']:
            return False, "ℹ️ Уже в группе"
        
        return True, ""
    
    def can_leave(self, capt_info: dict, user_id: int) -> tuple[bool, str]:
        if str(user_id) not in capt_info['current_members']:
            return False, "ℹ️ Не в группе"
        
        return True, ""


class CaptMemberManager:
    def __init__(self):
        self.validator = None
    
    def set_validator(self, validator: CaptMemberValidator):
        self.validator = validator
    
    def format_members_list(self, members: list) -> str:
        if members:
            members_list = ""
            for i, member_id in enumerate(members, 1):
                members_list += f"**{i}.** <@{member_id}>\n"
            return members_list
        return "*Пока нет участников*"
    
    async def handle_join(self, interaction: discord.Interaction, max_members: int):
        capt_info = get_capt(interaction.guild_id, interaction.message.id)
        if not capt_info:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Группа не найдена в системе.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.validator = CaptMemberValidator(max_members)
        can_join, error_title = self.validator.can_join(capt_info, interaction.user.id)
        
        if not can_join:
            description = "Максимальное количество участников: **{max_members}**" if "заполнена" in error_title else "Вы уже являетесь участником этой группы."
            embed = discord.Embed(
                title=error_title,
                description=description,
                color=0xff6b35 if "заполнена" in error_title else 0x3742fa
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        success = add_member_to_capt(interaction.guild_id, interaction.message.id, interaction.user.id)
        if not success:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Не удалось присоединиться к группе. Попробуйте позже.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await self._update_group_display(interaction, max_members)
        
        success_embed = discord.Embed(
            title="🎉 Успешно!",
            description="Вы присоединились к группе!",
            color=0x2ed573
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
        capt_info = get_capt(interaction.guild_id, interaction.message.id)
        current_count = len(capt_info['current_members'])
        
        if current_count >= max_members:
            await self._handle_group_completion(interaction, max_members, capt_info)
    
    async def handle_leave(self, interaction: discord.Interaction, max_members: int):
        capt_info = get_capt(interaction.guild_id, interaction.message.id)
        if not capt_info:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Группа не найдена в системе.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.validator = CaptMemberValidator(max_members)
        can_leave, error_title = self.validator.can_leave(capt_info, interaction.user.id)
        
        if not can_leave:
            embed = discord.Embed(
                title=error_title,
                description="Вы не являетесь участником этой группы.",
                color=0x3742fa
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        success = remove_member_from_capt(interaction.guild_id, interaction.message.id, interaction.user.id)
        if not success:
            embed = discord.Embed(
                title="❌ Ошибка",
                description="Не удалось покинуть группу. Попробуйте позже.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await self._update_group_display(interaction, max_members)
        
        leave_embed = discord.Embed(
            title="👋 Вы покинули группу",
            description="Вы успешно покинули группу.",
            color=0xff6b35
        )
        await interaction.response.send_message(embed=leave_embed, ephemeral=True)
    
    async def _update_group_display(self, interaction: discord.Interaction, max_members: int):
        capt_info = get_capt(interaction.guild_id, interaction.message.id)
        current_count = len(capt_info['current_members'])
        members_list = self.format_members_list(capt_info['current_members'])
        
        embed = EmbedBuilder.create_capt_embed(current_count, max_members, members_list)
        
        view = CaptView(max_members)
        await interaction.message.edit(embed=embed, view=view)
    
    async def _handle_group_completion(self, interaction: discord.Interaction, max_members: int, capt_info: dict):
        import asyncio
        
        await asyncio.sleep(2)
        
        members_list = self.format_members_list(capt_info['current_members'])
        final_embed = EmbedBuilder.create_final_capt_embed(max_members, members_list)
        
        await interaction.channel.send(embed=final_embed)
        
        await asyncio.sleep(3)
        try:
            await interaction.message.delete()
            remove_capt(interaction.guild_id, interaction.message.id)
        except:
            pass


class DenyReasonModal(BaseModal, title="Причина отказа"):
    reason = TextInput(
        label="Укажите причину отказа",
        placeholder="Например: Сейчас у нас нет мест.",
        style=discord.TextStyle.paragraph
    )

    def __init__(self, applicant_id: str, message: discord.Message, reviewer: discord.User, message_id: str, bot):
        super().__init__(title="Причина отказа")
        self.applicant_id = applicant_id
        self.message = message
        self.reviewer = reviewer
        self.message_id = message_id
        self.notification_sender = NotificationSender(bot)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            await self.handle_error(interaction, "Ошибка: сервер не определён.")
            return

        embed = self.message.embeds[0]
        embed.add_field(name="Рассмотрел заявку", value=self.reviewer.mention, inline=False)
        embed.add_field(name="Причина отказа", value=f"`{self.reason.value}`", inline=False)

        new_view = View()
        denied_button = Button(label="❌ Отклонено", style=discord.ButtonStyle.red, disabled=True)
        new_view.add_item(denied_button)

        await self.message.edit(embed=embed, view=new_view)

        application_state_manager.remove_state(self.message_id)
        
        remove_application(interaction.guild_id, self.message_id)

        notification_sent = await self.notification_sender.send_denial_notification(self.applicant_id, self.reason.value)
        
        if notification_sent:
            await interaction.response.send_message("Заявка отклонена. Пользователю отправлено уведомление.", ephemeral=True)
        else:
            await interaction.response.send_message("Заявка отклонена, но не удалось отправить сообщение пользователю.", ephemeral=True)


class ApplicationView(BaseView):
    def __init__(self, applicant_id: str, message_id: str, guild_id: int, bot):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.message_id = message_id
        self.guild_id = guild_id
        self.bot = bot
        self.reviewer = ApplicationReviewer(self)
        self.notification_sender = NotificationSender(bot)
        self._setup_buttons()

    def _setup_buttons(self):
        self.approve_button = Button(
            label="✅ Принять",
            style=discord.ButtonStyle.green,
            custom_id=f"approve_{self.message_id}"
        )
        self.deny_button = Button(
            label="❌ Отклонить",
            style=discord.ButtonStyle.red,
            custom_id=f"deny_{self.message_id}"
        )

        self.approve_button.callback = self.approve
        self.deny_button.callback = self.deny
        self.add_item(self.approve_button)
        self.add_item(self.deny_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        has_permission = await check_approver(interaction)
        if not has_permission:
            await self.handle_error(interaction, "У вас нет прав для взаимодействия с этой заявкой.")
            return False
        return True

    async def _check_reviewer_status(self, interaction: discord.Interaction) -> bool:
        message_id = str(self.message_id)
        is_being_reviewed, reviewer_id = self.reviewer.is_being_reviewed(message_id, interaction.user.id)
        
        if is_being_reviewed:
            reviewer = interaction.guild.get_member(reviewer_id)
            tag = reviewer.mention if reviewer else f"<@{reviewer_id}>"
            await self.handle_error(interaction, f"Сейчас заявку смотрит {tag}.")
            return False
        
        self.reviewer.set_reviewer(message_id, interaction.user.id)
        return True

    async def approve(self, interaction: discord.Interaction):
        if not await self._check_reviewer_status(interaction):
            return

        await interaction.response.defer()

        if interaction.guild_id is None:
            await interaction.followup.send("Ошибка: сервер не определён.", ephemeral=True)
            return

        notification_sent = await self.notification_sender.send_approval_notification(self.applicant_id)
        if not notification_sent:
            await interaction.followup.send("Не удалось отправить сообщение пользователю.", ephemeral=True)

        role_assigned = await RoleManager.assign_approved_role(interaction.guild, self.applicant_id)
        if not role_assigned:
            await interaction.followup.send("Не удалось выдать роль пользователю.", ephemeral=True)

        embed = interaction.message.embeds[0]
        embed.add_field(name="Рассмотрел заявку", value=interaction.user.mention, inline=False)

        new_view = View()
        approved_button = Button(label="✅ Принято", style=discord.ButtonStyle.green, disabled=True)
        new_view.add_item(approved_button)

        await interaction.message.edit(embed=embed, view=new_view)

        self.reviewer.clear_reviewer(str(self.message_id))
        
        remove_application(interaction.guild_id, self.message_id)

    async def deny(self, interaction: discord.Interaction):
        if not await self._check_reviewer_status(interaction):
            return

        await interaction.response.send_modal(DenyReasonModal(
            applicant_id=self.applicant_id,
            message=interaction.message,
            reviewer=interaction.user,
            message_id=str(self.message_id),
            bot=self.bot
        ))


class FormMessageModal(BaseModal, title="Настройка формы заявок"):
    form_title = TextInput(label="Заголовок формы", max_length=256)
    form_description = TextInput(
        label="Описание формы",
        placeholder="Описание вашей формы",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    form_image = TextInput(
        label="URL картинки (необязательно)",
        max_length=500,
        required=False
    )
    form_color = TextInput(
        label="Цвет формы (HEX)",
        placeholder="Например: #FF5733",
        max_length=7,
        required=False
    )

    def __init__(self, channel_id):
        super().__init__(title="Настройка формы заявок")
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create_form_embed(
            self.form_title.value,
            self.form_description.value,
            self.form_color.value,
            self.form_image.value
        )

        bot = interaction.client
        view = ApplyButtonView(bot)
        channel = interaction.guild.get_channel(int(self.channel_id))
        
        if channel is None:
            await self.handle_error(interaction, "Ошибка: указанный канал не найден.")
            return
            
        await channel.send(embed=embed, view=view)
        save_settings(interaction.guild_id, form_channel_id=self.channel_id)
        await interaction.response.send_message("Форма для заявок создана!", ephemeral=True)


class ApplicationModal(BaseModal, title="Заявка на вступление"):
    name = TextInput(
        label="1. Как тебя зовут? (IRL)",
        placeholder="Настоящее имя НЕ игровое",
        max_length=100
    )
    age = TextInput(
        label="2. Сколько тебе лет?",
        placeholder="IRL возраст",
        max_length=10
    )
    families = TextInput(
        label="3. В каких семьях был на проекте?",
        placeholder="Если был, то почему ушел?",
        style=discord.TextStyle.paragraph
    )
    favorite = TextInput(
        label="4. Любимое занятие",
        placeholder="Что тебе нравится делать больше всего?",
        style=discord.TextStyle.paragraph
    )
    expectations = TextInput(
        label="5. Чего ждешь от семьи?",
        placeholder="Что можешь предложить семье сам?",
        style=discord.TextStyle.paragraph
    )

    def __init__(self, bot):
        super().__init__(title="Заявка на вступление")
        self.bot = bot

    def _get_form_data(self) -> dict:
        return {
            'name': self.name.value,
            'age': self.age.value,
            'families': self.families.value,
            'favorite': self.favorite.value,
            'expectations': self.expectations.value
        }

    def _get_embed_data(self, embed: discord.Embed) -> dict:
        return {
            'title': embed.title,
            'description': embed.description,
            'color': embed.color.value,
            'thumbnail': {'url': embed.thumbnail.url} if embed.thumbnail else None,
            'fields': [{'name': f.name, 'value': f.value, 'inline': f.inline} for f in embed.fields],
            'footer': {'text': embed.footer.text} if embed.footer else None
        }

    async def on_submit(self, interaction: discord.Interaction):
        form_channel_id, approv_channel_id, approver_role_id, _ = get_settings(interaction.guild_id)
        
        if not approv_channel_id:
            await self.handle_error(interaction, "Ошибка! Канал для заявок не настроен.")
            return

        channel = interaction.guild.get_channel(int(approv_channel_id))
        if channel is None:
            await self.handle_error(interaction, "Ошибка: канал для заявок не найден.")
            return

        init_owners()
        guild_id_str = str(interaction.guild_id)
        approver_role_id = owners_cache.get('approver_role_ids', {}).get(guild_id_str)

        role = None
        if approver_role_id:
            role = interaction.guild.get_role(int(approver_role_id))

        mention = role.mention if role else "@everyone"

        form_data = self._get_form_data()
        embed = EmbedBuilder.create_application_embed(interaction.user, form_data)

        view = ApplicationView(
            applicant_id=str(interaction.user.id),
            message_id="temp",
            guild_id=interaction.guild_id,
            bot=self.bot
        )
        content = f"{mention} {interaction.user.mention}"
        message = await channel.send(content=content, embed=embed, view=view)

        view = ApplicationView(
            applicant_id=str(interaction.user.id),
            message_id=str(message.id),
            guild_id=interaction.guild_id,
            bot=self.bot
        )
        await message.edit(view=view)

        embed_data = self._get_embed_data(embed)
        save_application(interaction.guild_id, channel.id, message.id, interaction.user.id, embed_data)

        await interaction.response.send_message("Заявка в семью успешно отправлена!", ephemeral=True)


class ApplyButtonView(BaseView):
    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Подать заявку", style=discord.ButtonStyle.blurple, custom_id="apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        form_channel_id, approv_channel_id, approver_role_id, _ = get_settings(interaction.guild_id)
        
        if not approv_channel_id:
            await self.handle_error(interaction, "Ошибка! Канал для заявок не настроен.")
            return
            
        await interaction.response.send_modal(ApplicationModal(self.bot))


class CaptView(View):
    def __init__(self, max_members):
        super().__init__(timeout=None)
        self.max_members = max_members
        self.member_manager = CaptMemberManager()
        self._setup_buttons()
    
    def _setup_buttons(self):
        join_button = Button(
            style=discord.ButtonStyle.primary,
            label="🔗 Присоединиться",
            custom_id="join_capt",
            emoji="👥"
        )
        join_button.callback = self.join_callback
        self.add_item(join_button)
        
        leave_button = Button(
            style=discord.ButtonStyle.secondary,
            label="❌ Покинуть",
            custom_id="leave_capt",
            emoji="🚪"
        )
        leave_button.callback = self.leave_callback
        self.add_item(leave_button)
    
    async def join_callback(self, interaction: discord.Interaction):
        try:
            await self.member_manager.handle_join(interaction, self.max_members)
        except Exception as e:
            print(f"Ошибка в обработке кнопки присоединения к группе: {e}")
            error_embed = discord.Embed(
                title="❌ Системная ошибка",
                description="Произошла непредвиденная ошибка. Обратитесь к администратору.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    async def leave_callback(self, interaction: discord.Interaction):
        try:
            await self.member_manager.handle_leave(interaction, self.max_members)
        except Exception as e:
            print(f"Ошибка в обработке кнопки покидания группы: {e}")
            error_embed = discord.Embed(
                title="❌ Системная ошибка",
                description="Произошла непредвиденная ошибка. Обратитесь к администратору.",
                color=0xff4757
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)