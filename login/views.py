import datetime
import hashlib

from django.conf import settings
from django.shortcuts import render, redirect

# Create your views here.
from login import models, forms


def index(request):
    return render(request, 'login/index.html')


def login(request):
    if request.session.get('is_login', None):  # 不允许重复登录
        return redirect('/index/')
    if request.method == "POST":
        #username = request.POST.get('username', None)
        #password = request.POST.get('password', None)
        login_form = forms.UserForm(request.POST)  # 创建登录表单，用请求对象中的POST参数填充表单
        message = "检查填写的内容!"
        #if username and password:
            #username = username.strip()
            #print(username, password)
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            try:
                user = models.User.objects.get(name=username)  # 数据查询API,通过输入的用户名查询数据库
                if not user.has_confirmed:
                    message = '该用户还没有通过邮件确认.'
                    return render(request, 'login/login.html', locals())
                if user.password == hash_code(password): # 表单的密码哈希值和DB中密码对比
                    # 向session字典写入用户状态和数据
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    return redirect('/index/')
                else:
                    message = "密码错误！"
            except:
                message = "用户名不存在!"
        return render(request, 'login/login.html', locals())
    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())


def register(request):
    if request.session.get('is_login', None): # 已经登录的不能注册
        return redirect('/index/')

    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = '请检查填写的内容。'
        if register_form.is_valid():
            username = register_form.cleaned_data['username'] # 获取注册表单(字典结构)中填写的合法数据，存放在变量中
            password1 = register_form.cleaned_data['password1']
            password2 = register_form.cleaned_data['password2']
            email = register_form.cleaned_data['email']
            sex = register_form.cleaned_data['sex']
            if password1 != password2:
                message = "两次输入的密码不一致!"
                return render(request, 'login/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=username)
                if same_name_user:
                    message = '用户已经存在，重新输入一个用户名.'
                    return render(request, 'login/register.html', locals())
                same_email_user = models.User.objects.filter(email=email)
                if same_email_user:
                    message = '该电子邮箱已经被注册，请重新填入一个.'
                    return render(request, 'login/register.html', locals())

                new_user = models.User()
                new_user.name = username
                new_user.password = hash_code(password1) # 加密密码
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                send_email(email, code)
                message = '请前往注册邮箱,点击链接进行邮件确认。'
                return render(request, 'login/confirm.html', locals()) # 显示邮件确认页面
    # GET方式时
    register_form = forms.RegisterForm()
    return render(request, 'login/register.html', locals())


def logout(request):
    if not request.session.get('is_login', None): # 如果没有登录
        return redirect('/index/')
    request.session.flush() # 删除session数据
    return redirect('/index/')


# 生成哈希码，可以用于密码加密；生成token值
def hash_code(s, salt='mysite'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode()) # update方法接受bytes类型
    return h.hexdigest()


# 创建确认码
def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code


# 发邮件
def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives
    subject = "来自www.liujiangblog.com的注册确认邮件"
    text_content = '''感谢注册www.liujiangblog.com，这里是刘江的博客和教程站点，专注于Python和Django技术的分享！
                    如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''
    html_content = '''<p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.liujiangblog.com</a>，
                    这里是刘江的博客和教程站点，专注于Python和Django技术的分享！</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>'''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code) # 邮件中的确认信息
    except:
        # 当code是伪造的或者code已经被使用过再次使用时，点击邮件中的链接显示的信息如下
        message = '无效的确认请求'
        return render(request, 'login/confirm.html', locals())
    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '你的邮件已经过期了，请重新注册。'
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '您注册成功了，请登录。'
        return render(request, 'login/confirm.html', locals())