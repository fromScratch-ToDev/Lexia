import time
import re

# Dictionnaire des nombres de 1 à 2534 en toutes lettres
def create_number_dict():
    # Dictionnaires de base
    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    teens = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"]
    
    def number_to_words(n):
        if n == 0:
            return "zéro"
        
        result = ""
        
        # Milliers
        if n >= 1000:
            thousands = n // 1000
            if thousands == 1:
                result += "mille"
            else:
                result += number_to_words(thousands) + " mille"
            n %= 1000
            if n > 0:
                result += " "
        
        # Centaines
        if n >= 100:
            hundreds = n // 100
            if hundreds == 1:
                result += "cent"
            else:
                result += units[hundreds] + " cent"
            n %= 100
            if n > 0:
                result += " "
        
        # Dizaines et unités
        if n >= 20:
            tens_digit = n // 10
            units_digit = n % 10
            
            if tens_digit == 7:  # 70-79
                result += "soixante"
                if units_digit == 0:
                    result += "-dix"
                elif units_digit == 1:
                    result += " et onze"
                else:
                    result += "-" + teens[units_digit]
            elif tens_digit == 9:  # 90-99
                result += "quatre-vingt"
                if units_digit == 0:
                    result += "-dix"
                elif units_digit == 1:
                    result += " et onze"
                else:
                    result += "-" + teens[units_digit]
            else:
                result += tens[tens_digit]
                if units_digit > 0:
                    if tens_digit == 8 and units_digit == 0:
                        result += "s"
                    elif units_digit == 1 and tens_digit in [2, 3, 4, 5, 6]:
                        result += " et " + units[units_digit]
                    else:
                        result += "-" + units[units_digit]
        elif n >= 10:
            result += teens[n - 10]
        elif n > 0:
            result += units[n]
        
        return result
    
    # Créer le dictionnaire
    number_dict = {}
    for i in range(1, 2535):
        number_dict[number_to_words(i)] = i
    
    return number_dict

def check_if_article_asked(user_message: str) -> bool:
    """
    Vérifie si l'utilisateur a demandé un article du code civil.
    """
    # Liste des mots-clés pour détecter une demande d'article
    keywords = [
        "article", "articles", 
        "art", "art.", "art°", "art:",
        "articl", "artcile", "artical", "artilce", "aticle", "ariticle",
        "texte", "textes",
        "clause", "clauses",
    ]
    
    # Convertir le message en minuscules pour une comparaison insensible à la casse
    user_message_lower = user_message.lower()
    
    # Vérifier si l'un des mots-clés est présent dans le message
    return any(keyword in user_message_lower for keyword in keywords)

# Créer le dictionnaire
numbers_dict = create_number_dict()

def find_numbers_in_string(input_string):
    """
    Parcourt le dictionnaire pour trouver des nombres (clés et valeurs) dans la chaîne d'entrée.
    Retourne une liste avec tous les nombres trouvés.
    """

    if not check_if_article_asked(input_string):
        return []

    found_numbers : list[str] = []

    input_lower = input_string.lower()
    
    # Trouver les nombres en lettres (trier par longueur décroissante pour éviter les sous-chaînes)
    word_matches = []
    for word_key, number_value in numbers_dict.items():
        if word_key in input_lower:
            word_matches.append((word_key, number_value, len(word_key)))
    
    # Trier par longueur décroissante pour prioriser les matches les plus longs
    word_matches.sort(key=lambda x: x[2], reverse=True)
    
    # Garder seulement les matches qui ne se chevauchent pas
    used_positions = set()
    for word_key, number_value, length in word_matches:
        start_pos = input_lower.find(word_key)
        while start_pos != -1:
            end_pos = start_pos + length
            # Vérifier si cette position n'est pas déjà utilisée
            if not any(pos in used_positions for pos in range(start_pos, end_pos)):
                found_numbers.append(str(number_value))
                used_positions.update(range(start_pos, end_pos))
                break
            start_pos = input_lower.find(word_key, start_pos + 1)
    
    # Trouver les nombres en chiffres (utiliser des limites de mots)
    digit_matches = re.findall(r'\b\d+\b', input_string)
    for match in digit_matches:
        number = int(match)
        if number in numbers_dict.values():
            found_numbers.append(str(number))
    
    # Supprimer les doublons tout en préservant l'ordre
    seen = set()
    unique_numbers = []
    for num in found_numbers:
        if num not in seen:
            seen.add(num)
            unique_numbers.append(num)
    

    
    return unique_numbers




if __name__ == "__main__":
    
    start_time = time.time()

    # Tester quelques conversions
    print(numbers_dict["quatre-vingt-dix-neuf"])  # 99
    print(numbers_dict["mille deux cent trente-quatre"])  # 1234
    print(numbers_dict["deux mille cinq cent trente-deux"])  # 2532

    # Tester la fonction find_numbers_in_string
    test_string = "J'ai vingt-trois ans et mon frère a trente-cinq ans. Nous habitons au 1234 rue de la Paix."
    print(f"Chaîne de test: {test_string}")
    print(f"Nombres trouvés: {find_numbers_in_string(test_string)}")

    test_string2 = "Il y a cent cinquante étudiants et 75 professeurs dans cette école."
    print(f"\nChaîne de test 2: {test_string2}")
    print(f"Nombres trouvés: {find_numbers_in_string(test_string2)}")

    test_string3 = """
    Dans cette grande entreprise de deux mille quatre cent douze employés, il y a quatre-vingt-dix-sept ingénieurs, cent vingt-trois comptables, trois cent quarante-cinq commerciaux, et sept cent quatre-vingt-neuf ouvriers. Le siège social se trouve au 1847 boulevard de la République, dans un bâtiment de quinze étages inauguré en mille neuf cent quatre-vingt-quatorze.
    Le chiffre d'affaires annuel est de deux milliards trois cent cinquante millions d'euros. En outre, l'entreprise a investi quatre-vingt-dix millions d'euros dans la recherche et le développement cette année. Au total, elle possède quatre-vingt-dix-neuf brevets actifs et a déposé cent cinquante demandes de brevets supplémentaires.
    Bien que l'entreprise ait connu une croissance de vingt pour cent par rapport à l'année précédente, elle a également dû faire face à des défis, notamment une baisse de la productivité de quinze pour cent dans certains départements. Malgré cela, le moral des employés reste élevé, avec quatre-vingt-dix-huit pour cent d'entre eux se déclarant satisfaits de leur travail.
    """
    print(f"\nChaîne de test 3: {test_string3}")
    print(f"Nombres trouvés: {find_numbers_in_string(test_string3)}")

    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Temps d'exécution: {execution_time:.6f} secondes")