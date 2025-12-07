# RECORDER-ED - Educational Platform

A modern Django web application showcasing a comprehensive design system built with **Django-Tailwind**, **DaisyUI**, and **Alpine.js**.

## 🚀 Features

### Design System

- **Modern UI Components**: Comprehensive set of reusable components
- **Tailwind CSS Integration**: Professional styling with utility-first approach
- **DaisyUI Components**: Beautiful, accessible UI components
- **Alpine.js Interactivity**: Lightweight JavaScript framework for dynamic behavior
- **Responsive Design**: Mobile-first approach with responsive layouts

### Component Library

- **Cards**: Multiple variants (default, course, testimonial, notification)
- **Buttons**: Various styles, sizes, and states with icon support
- **Forms**: Beautiful, accessible forms with validation
- **Stats Cards**: Data visualization components
- **Badges**: Status and category indicators
- **Alerts**: Success, warning, error, and info notifications
- **Modals**: Interactive dialogs with different sizes
- **Tabs**: Dynamic tab navigation
- **Dropdowns**: Context menus and selection components
- **Progress Bars**: Visual progress indicators
- **Breadcrumbs**: Navigation helpers
- **Pagination**: Data navigation

### Interactive Features

- **Theme Switching**: Multiple DaisyUI themes (Light, Dark, Cupcake, Cyberpunk)
- **Live Notifications**: Toast-style notifications with Alpine.js
- **Dynamic Tabs**: Client-side tab switching
- **Responsive Navigation**: Mobile-friendly navigation with dropdowns
- **Form Interactions**: Real-time form validation and feedback

## 🛠 Technology Stack

- **Backend**: Django 5.2.7
- **Frontend**: Django-Tailwind + DaisyUI + Alpine.js
- **Styling**: Tailwind CSS with utility-first approach
- **Components**: DaisyUI for pre-built components
- **Interactivity**: Alpine.js for reactive behavior
- **Icons**: Heroicons SVG icon set
- **Build Tools**: Node.js, PostCSS, Autoprefixer

## 📦 Installation & Setup

### Prerequisites

- Python 3.12+
- Node.js 16+
- npm or yarn

### 1. Clone and Setup Virtual Environment

```bash
cd recordered
python -m venv virtenv
source virtenv/bin/activate  # On Windows: virtenv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Install Django-Tailwind

```bash
pip install \"django-tailwind[reload]\"
pip install django-browser-reload
```

### 3. Configure Django Settings

The project is already configured with:

- `tailwind` app for Tailwind CSS
- `theme` app for custom Tailwind theme
- `django_browser_reload` for live reloading
- All necessary middleware and settings

### 4. Initialize Tailwind CSS

```bash
python manage.py tailwind install
```

### 5. Apply Migrations

```bash
python manage.py migrate
```

### 6. Run Development Servers

**Terminal 1 - Django Server:**

```bash
python manage.py runserver
```

**Terminal 2 - Tailwind Watch:**

```bash
python manage.py tailwind start
```

Your application will be available at `http://127.0.0.1:8000/`

## 🎨 Using the Design System

### Template Tags

Load the design system in your templates:

```django
{% load design_system %}
```

### Component Examples

#### Stat Cards

```django
{% stat_card icon=\"users\" value=\"2,500+\" label=\"Students\" color=\"primary\" %}
```

#### Buttons

```django
{% button \"Get Started\" variant=\"primary\" color=\"primary\" size=\"lg\" %}
{% button \"Download\" variant=\"outline\" color=\"secondary\" icon=\"check\" %}
```

#### Cards

```django
{% card title=\"Course Title\" content=\"Description\" variant=\"course\" image=\"/path/to/image.jpg\" price=299 rating=4.8 students=1250 %}
```

#### Badges

```django
{% badge \"New\" color=\"primary\" %}
{% badge \"Hot\" color=\"error\" size=\"lg\" %}
```

#### Alerts

```django
{% alert \"Success message!\" type=\"success\" %}
{% alert \"Warning message!\" type=\"warning\" dismissible=True %}
```

#### Progress Bars

```django
{% progress_bar value=75 max_value=100 color=\"primary\" label=\"Course Progress\" %}
```

#### Icons

```django
{% icon \"users\" size=\"w-6 h-6\" extra_classes=\"text-blue-500\" %}
```

### Alpine.js Integration

#### Basic Component

```html
<div x-data=\"{ open: false }\">
    <button @click=\"open = !open\" class=\"btn btn-primary\">
        Toggle
    </button>
    <div x-show=\"open\" x-transition>
        Content here
    </div>
</div>
```

#### Dynamic Data

```html
<div x-data=\"{ items: {{ items|json_script }} }\">
    <template x-for=\"item in items\" :key=\"item.id\">
        <div x-text=\"item.name\"></div>
    </template>
</div>
```

## 🎭 Available Themes

The application supports multiple DaisyUI themes:

- **Light**: Clean, bright theme for daytime use
- **Dark**: Dark theme for low-light environments
- **Cupcake**: Playful, colorful theme
- **Cyberpunk**: Futuristic, neon theme

Switch themes using the theme dropdown in the navigation bar.

## 📱 Responsive Design

All components are built with mobile-first responsive design:

- **Mobile**: Single column layouts, touch-friendly interactions
- **Tablet**: Optimized for medium screens
- **Desktop**: Full-featured layouts with sidebars and complex grids

## 🔧 Customization

### Adding New Components

1. **Create Template Tag**:

```python
# apps/core/templatetags/design_system.py
@register.inclusion_tag('components/my_component.html')
def my_component(param1, param2='default'):
    return {
        'param1': param1,
        'param2': param2,
    }
```

2. **Create Template**:

```html
<!-- templates/components/my_component.html -->
<div class=\"my-component {{ param2 }}\">
    {{ param1 }}
</div>
```

3. **Use in Templates**:

```django
{% load design_system %}
{% my_component \"Hello World\" param2=\"custom-class\" %}
```

### Customizing Tailwind

Edit `theme/static_src/src/styles.css` to add custom styles:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .my-custom-component {
    @apply bg-blue-500 text-white p-4 rounded-lg;
  }
}
```

### Adding New Icons

Add to the icons dictionary in `design_system.py`:

```python
icons = {
    # ... existing icons
    'my-icon': '<svg class=\"{size} {extra}\" ...>...</svg>',
}
```

## 📊 Example Pages

The application includes four example pages:

1. **Home** (`/`): Landing page with hero section, stats, and featured courses
2. **Components** (`/components/`): Showcase of all available components
3. **Forms** (`/forms/`): Examples of form styling and validation
4. **Interactive** (`/interactive/`): Alpine.js powered interactive components

## 🚀 Production Deployment

### Build for Production

```bash
python manage.py tailwind build
python manage.py collectstatic
```

### Environment Variables

```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the example implementations

---

**Built with ❤️ using Django, Tailwind CSS, DaisyUI, and Alpine.js**
