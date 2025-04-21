import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import random

def scrape_nintendo_eshop(target_count=1000, max_retries=3):
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    games_data = []
    game_urls = []
    base_url = "https://www.nintendo.com/es-es/Buscar/Buscar-299117.html?f=147394-5-82-21991"
    
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 7)

    def safe_get(url, retries=3):
        for attempt in range(retries):
            try:
                driver.get(url)
                return True
            except TimeoutException:
                print(f"Timeout al cargar {url}, reintento {attempt + 1}/{retries}")
                if attempt == retries - 1:
                    return False
                time.sleep(random.uniform(0.5, 1.5))
    
    try:
        page_num = 1
        while len(game_urls) < target_count:
            current_url = f"{base_url}&p={page_num}" if page_num > 1 else base_url
            
            if not safe_get(current_url):
                print(f"No se pudo cargar la página {page_num}")
                break
            
            try:
                cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Aceptar todas')]")))
                cookie_btn.click()
                time.sleep(random.uniform(0.5, 1.5))
            except:
                pass
            
            try:
                games = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.searchresult_row a")))
                new_urls = [game.get_attribute("href") + "#gameDetails" for game in games if game.get_attribute("href")]
                
                if not new_urls:
                    print("No se encontraron más juegos")
                    break
                
                game_urls.extend(new_urls)
                print(f"Página {page_num}: {len(game_urls)} URLs recolectadas")
                
            except Exception as e:
                print(f"Error extrayendo URLs: {str(e)}")
                break
            
            page_num += 1
            time.sleep(random.uniform(1, 3))
        
        print(f"\nIniciando extracción de {min(target_count, len(game_urls))} juegos...")
        
        for i, url in enumerate(game_urls[:target_count], 1):
            for attempt in range(max_retries):
                try:
                    if not safe_get(url):
                        continue
                    
                    game_info = {
                        "Título": "No disponible",
                        "Clasificación": "No disponible",
                        "Precio": "No disponible",
                        "Categorías": "No disponible",
                        "Distribuidor": "No disponible",
                        "Desarrollador": "No disponible",
                        "Fecha de lanzamiento": "No disponible",
                    }
                    
                    try:
                        game_info["Título"] = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.gamepage-header-info h1"))
                        ).text.strip()
                    except:
                        pass
                    
                    try:
                        meta_elements = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.gamepage-header-meta"))
                        )
                        for meta in meta_elements:
                            if "Fecha de lanzamiento:" in meta.text:
                                game_info["Fecha de lanzamiento"] = meta.text.split(":")[1].strip()
                                break
                    except:
                        pass
                    
                    try:
                        clasificacion_element = driver.find_element(By.XPATH, "//p[contains(text(), 'Clasificación por edades')]/following-sibling::p")
                        game_info["Clasificación"] = clasificacion_element.text.strip()
                    except:
                        pass
                    
                    try:
                        container = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.game_info_container"))
                        )
                        
                        mapping = {
                            "Categorías": "Categorías",
                            "Distribuidor": "Distribuidor",
                            "Desarrollador": "Desarrollador"
                        }
                        
                        for field, text in mapping.items():
                            try:
                                element = container.find_element(By.XPATH, f".//p[contains(text(), '{text}')]/following-sibling::p")
                                game_info[field] = element.text.strip()
                            except:
                                continue
                    except:
                        pass
                    
                    try:
                        game_info["Precio"] = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.plm-price__main"))
                        ).text.strip()
                    except:
                        pass
                    
                    games_data.append(game_info)
                    
                    if i % 50 == 0:
                        pd.DataFrame(games_data).to_csv('juegos_nintendo_progreso.csv', index=False, encoding='utf-8-sig')
                        print(f"Progreso guardado: {i} juegos procesados")
                    
                    break
                
                except Exception as e:
                    print(f"Error procesando juego {i} (intento {attempt + 1}): {str(e)}")
                    if attempt == max_retries - 1:
                        continue
                    time.sleep(random.uniform(2, 5))
            
            time.sleep(random.uniform(0.5, 2.5))
        
        if games_data:
            df = pd.DataFrame(games_data)
            df.to_csv('juegos_nintendo_completo.csv', index=False, encoding='utf-8-sig')
            print(f"\nExtracción completada. Datos guardados en 'juegos_nintendo_completo.csv'")
            print(f"Total de juegos procesados: {len(games_data)}")
            return df
    
    except Exception as e:
        print(f"Error crítico: {str(e)}")
        if games_data:
            pd.DataFrame(games_data).to_csv('juegos_nintendo_parcial.csv', index=False, encoding='utf-8-sig')
            print("Datos parciales guardados en 'juegos_nintendo_parcial.csv'")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_nintendo_eshop(target_count=1000)
