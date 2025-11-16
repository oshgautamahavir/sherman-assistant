"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from pathlib import Path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('sherman.urls')),
]

# Serve frontend in production
if not settings.DEBUG:
    frontend_dir = Path(settings.BASE_DIR) / 'frontend' / 'dist'
    if frontend_dir.exists():
        # Serve static assets (JS, CSS, images) from frontend dist
        urlpatterns += [
            re_path(r'^assets/(?P<path>.*)$', serve, {
                'document_root': str(frontend_dir / 'assets'),
            }),
        ]

        # Serve index.html for all non-API routes (SPA routing)
        urlpatterns += [
            re_path(r'^(?!api|admin|static|assets).*$', serve, {
                'path': 'index.html',
                'document_root': str(frontend_dir),
            }),
        ]
else:
    # In development, redirect root to frontend dev server
    urlpatterns += [
        path('', RedirectView.as_view(url='http://localhost:5173', permanent=False)),
    ]

# Serve static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
