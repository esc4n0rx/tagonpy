import os
import sys
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, BaseLoader
from core.parser import TagonParser, TagonComponent

class TagonRenderer:
    """Renderizador de componentes .tg para HTML"""
    
    def __init__(self, template_dir: str = "templates", components_dir: str = "components"):
        self.parser = TagonParser()
        self.template_dir = template_dir
        self.components_dir = components_dir
        
        # Configura Jinja2 para templates
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )
    
    def render_component(self, component_path: str) -> str:
        """
        Renderiza um componente .tg para HTML completo (método original)
        """
        return self.render_component_with_context(component_path, {})
    
    def render_component_with_context(self, component_path: str, external_context: Dict[str, Any] = None) -> str:
        """
        Renderiza um componente .tg com contexto externo (NOVO)
        
        Args:
            component_path: Caminho para o arquivo .tg
            external_context: Contexto adicional do sistema de roteamento
            
        Returns:
            str: HTML renderizado
        """
        if external_context is None:
            external_context = {}
            
        try:
            print(f"🔍 Parseando componente: {component_path}")
            
            # Parseia o componente
            component = self.parser.parse_file(component_path)
            
            print(f"📦 Imports: {len(component.imports)} chars")
            print(f"⚙️ Functions: {len(component.functions)} chars")
            print(f"🎨 HTML: {len(component.html)} chars")
            print(f"🎨 CSS inline: {len(component.css)} chars")
            
            # Busca arquivo CSS externo
            external_css = self._load_external_css(component_path)
            print(f"📂 CSS externo: {len(external_css)} chars")
            
            # Combina CSS inline + externo
            combined_css = self._combine_css(component.css, external_css)
            print(f"🎨 CSS total: {len(combined_css)} chars")
            
            # Executa imports e funções do componente
            component_context = self._execute_component_logic(component)
            
            # NOVO: Mescla contexto do componente com contexto externo do roteamento
            merged_context = {**component_context, **external_context}
            
            print(f"🧮 Context total: {list(merged_context.keys())}")
            
            # Renderiza HTML usando Jinja2 com contexto mesclado
            html_content = self._render_html(component.html, merged_context)
            
            print(f"✅ HTML renderizado: {len(html_content)} chars")
            
            return self._render_final_html(html_content, combined_css, component_path)
            
        except Exception as e:
            print(f"❌ Erro no renderer: {str(e)}")
            return self._render_error_page(str(e))
    
    # ... resto dos métodos permanecem iguais ...
    def _load_external_css(self, component_path: str) -> str:
        """
        Carrega arquivo CSS externo correspondente ao componente
        
        Args:
            component_path: Caminho do arquivo .tg
            
        Returns:
            str: Conteúdo do CSS externo ou string vazia
        """
        try:
            # Determina o caminho do arquivo CSS
            component_name = os.path.splitext(os.path.basename(component_path))[0]
            css_path = os.path.join(self.components_dir, f"{component_name}.css")
            
            if os.path.exists(css_path):
                print(f"📂 Carregando CSS externo: {css_path}")
                with open(css_path, 'r', encoding='utf-8') as css_file:
                    css_content = css_file.read()
                print(f"✅ CSS externo carregado: {len(css_content)} chars")
                return css_content
            else:
                print(f"⚠️ CSS externo não encontrado: {css_path}")
                return ""
                
        except Exception as e:
            print(f"❌ Erro ao carregar CSS externo: {str(e)}")
            return ""
    
    def _combine_css(self, inline_css: str, external_css: str) -> str:
        """
        Combina CSS inline e externo com prioridades corretas
        
        Args:
            inline_css: CSS do arquivo .tg
            external_css: CSS do arquivo .css
            
        Returns:
            str: CSS combinado
        """
        combined = []
        
        # CSS externo primeiro (menor prioridade)
        if external_css.strip():
            combined.append("/* === CSS EXTERNO === */")
            combined.append(external_css.strip())
        
        # CSS inline depois (maior prioridade)
        if inline_css.strip():
            combined.append("\n/* === CSS INLINE === */")
            combined.append(inline_css.strip())
        
        # CSS adicional para garantir aplicação
        combined.append("""
/* === CSS DE GARANTIA === */
body {
    margin: 0 !important;
    padding: 0 !important;
}
""")
        
        result = "\n".join(combined)
        print(f"🔗 CSS combinado: {len(result)} chars")
        return result
    
    def _execute_component_logic(self, component: TagonComponent) -> Dict[str, Any]:
        """
        Executa imports e funções do componente
        
        Args:
            component: Componente parseado
            
        Returns:
            Dict: Contexto com funções e variáveis
        """
        context = {}
        
        try:
            # Executa imports
            if component.imports.strip():
                print(f"📥 Executando imports: {component.imports.strip()}")
                exec(component.imports, context)
            
            # Executa funções
            if component.functions.strip():
                print(f"⚙️ Executando funções: {component.functions.strip()}")
                exec(component.functions, context)
            
            # Remove imports desnecessários do contexto
            filtered_context = {}
            for k, v in context.items():
                if not k.startswith('__'):
                    if callable(v) or k in ['datetime', 'random', 'os']:
                        filtered_context[k] = v
            
            print(f"🧮 Context final: {list(filtered_context.keys())}")
            return filtered_context
            
        except Exception as e:
            print(f"❌ Erro ao executar lógica do componente: {e}")
            return {}
    
    def _render_html(self, html: str, context: Dict[str, Any]) -> str:
        """
        Renderiza HTML usando Jinja2 com contexto do componente
        
        Args:
            html: HTML template
            context: Contexto de variáveis e funções
            
        Returns:
            str: HTML renderizado
        """
        try:
            print(f"🎨 Renderizando HTML template com context: {list(context.keys())}")
            
            # Cria template temporário do HTML
            template = self.jinja_env.from_string(html)
            rendered = template.render(**context)
            
            print(f"✅ HTML template renderizado: {len(rendered)} chars")
            return rendered
            
        except Exception as e:
            print(f"❌ Erro na renderização HTML: {str(e)}")
            return f"<div class='error'>Erro na renderização: {str(e)}</div>"
    
    def _render_final_html(self, content: str, css: str, component_name: str) -> str:
        """
        Renderiza HTML final usando template base
        
        Args:
            content: Conteúdo HTML renderizado
            css: Estilos CSS combinados
            component_name: Nome do componente para título
            
        Returns:
            str: HTML final completo
        """
        try:
            print(f"🏗️ Montando HTML final com CSS: {len(css)} chars")
            
            # Verifica se template base existe
            template_path = os.path.join(self.template_dir, 'base.html')
            if os.path.exists(template_path):
                template = self.jinja_env.get_template('base.html')
                final_html = template.render(
                    title=f"TagonPy - {os.path.basename(component_name)}",
                    content=content,
                    component_css=css,
                    component_name=component_name
                )
                print(f"✅ HTML final renderizado: {len(final_html)} chars")
                return final_html
            else:
                print("⚠️ Template base não encontrado, usando fallback")
                return self._render_basic_template(content, css, component_name)
                
        except Exception as e:
            print(f"❌ Erro no template final: {str(e)}")
            # Fallback para template básico
            return self._render_basic_template(content, css, component_name)
    
    def _render_basic_template(self, content: str, css: str, component_name: str) -> str:
        """Template básico de fallback"""
        print("🔧 Usando template básico de fallback")
        
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TagonPy - {os.path.basename(component_name)}</title>
    <style>
        /* Reset básico */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
        }}
        
        /* CSS do componente */
        {css}
    </style>
</head>
<body>
    {content}
    
    <!-- Live Reload Script -->
    <script>
        console.log('🔗 Live Reload (Fallback) - Conectando...');
        
        const ws = new WebSocket('ws://localhost:3000/ws');
        
        ws.onopen = function() {{
            console.log('✅ Live reload conectado (fallback)');
        }};
        
        ws.onmessage = function(event) {{
            if (event.data === 'reload') {{
                console.log('🔄 Recarregando página...');
                location.reload();
            }}
        }};
        
        ws.onclose = function() {{
            console.log('❌ Live reload desconectado');
            setTimeout(() => {{
                location.reload();
            }}, 2000);
        }};
    </script>
</body>
</html>"""
    
    def _render_error_page(self, error: str) -> str:
        """Renderiza página de erro"""
        print(f"🚨 Renderizando página de erro: {error}")
        
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TagonPy - Erro</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .error-container {{
            max-width: 600px;
            background: rgba(239, 68, 68, 0.1);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(239, 68, 68, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
        }}
        
        h1 {{
            color: #ef4444;
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        
        p {{
            color: #a0a0a0;
            line-height: 1.6;
            margin: 1rem 0;
        }}
        
        .error-details {{
            background: rgba(0, 0, 0, 0.3);
            padding: 1rem;
            border-radius: 8px;
            font-family: Monaco, 'Courier New', monospace;
            font-size: 0.875rem;
            color: #ff6b6b;
            margin: 1rem 0;
            text-align: left;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>⚠️ Erro TagonPy</h1>
        <p>Ops! Algo deu errado ao processar seu componente.</p>
        <div class="error-details">{error}</div>
        <p><em>Verifique a sintaxe do seu arquivo .tg e .css e tente novamente.</em></p>
        <p>🔄 A página será recarregada automaticamente quando você salvar o arquivo.</p>
    </div>
    
    <script>
        // Auto-reload em caso de erro
        const ws = new WebSocket('ws://localhost:3000/ws');
        ws.onmessage = function(event) {{
            if (event.data === 'reload') {{
                location.reload();
            }}
        }};
    </script>
</body>
</html>"""