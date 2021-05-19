from tkinter import *
from tkinter import messagebox
import tkinter.font as font
from tkinter import ttk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from PIL import Image, ImageTk
from reader import Reader
from pdf_handler import *
import cv2
import re
import math

class MainWindow:
    def __init__(self, root):
        root.title("Numérisateur de formulaire")

        # Creation de la fenêtre
        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Définition du style
        title_font = font.Font(family='Arial', size=12)

        # Variables
        self.file = ''  # "file" et "image" font référence aux formulaires remplis à la main qu'on numérise
        self.form = ''  # À noté que "form" est utilisé pour signifier formulaire dans tout le programme
        self.img_data = dict()
        self.form_data = dict()
        self.form_bank = dict()
        self.clean_img = None
        self.image_id = None
        self.box_photo = None
        self.reader = None
        self.other_lang = StringVar(value="")
        self.lang = StringVar(value="fra")
        self.review_text = StringVar(value="Mot à corriger")
        self.review_index = IntVar(value=0)
        self.adapt_threshold = BooleanVar(value=False)
        self.conf_threshold = IntVar(value=80)
        self.denoise_factor = StringVar(value="40")
        self.scale_factor = StringVar(value="1.0")
        self.load_reader() # Crée instance permettant la lecture de document avec paramètres par défault

        #### Création des widgets dans la fenêtre
        ## Rangée 0
        head_label = ttk.Label(mainframe, text='Entrez vos formulaires pour la numerisation', font=title_font)
        head_label.grid(column=0, row=0, columnspan=3)

        ## Rangée 1
        self.add_empty_btn = ttk.Button(mainframe, text="Ajouter un format de formulaire",
                                   command=self.add_empty).grid(column=0, row=1, sticky=(N,S, E))
        self.add_image_btn = ttk.Button(mainframe, text="Numériser un formulaire",
                                   command=self.add_image).grid(column=1, row =1, sticky=(N,S,W))

        ## Rangée 2
        self.form_name_display = StringVar()
        self.empty_label = ttk.Label(mainframe, textvariable=self.form_name_display, font="TkFixedFont").grid(column=0, row=2)
        self.filename_display = StringVar()
        self.image_label = ttk.Label(mainframe, textvariable= self.filename_display, font="TkFixedFont").grid(column=1, row=2)

        ## Rangée 3
        # Affichage du texte a corriger
        self.review_display= ttk.Frame(mainframe, width = 250, height=80, borderwidth = 2, relief = 'sunken', padding="3 3 12 12")
        # Crée un Frame qui contient l'index, l'image et le texte détecté du champ
        self.index_display = Label(self.review_display, textvariable=self.review_index).grid(column=0, row=0, sticky=(N,S,E,W))
        self.image_display = Canvas(self.review_display, width = 200, height=80, background='gray80')
        self.text_display = Label(self.review_display, textvariable=self.review_text, font="TkFixedFont").grid(column=2, row=0, sticky = (N,S,E,W))
        self.image_display.grid(column=1, row=0,  sticky=(N,S,E,W), padx=10, pady=10)
        self.review_display.grid(column=0, row=3, columnspan=2, sticky = (E,W))
        # Affichage des statistiques
        self.stat_text = StringVar(value="Statistiques")
        self.stat_display = ttk.Label(mainframe, textvariable=self.stat_text, font="TkFixedFont", wraplength=350,relief="solid", borderwidth=1)\
            .grid(column=2, row = 2, sticky =(N,S,W), rowspan=4)

        ## Rangée 4
        self.change_field_btn = ttk.Button(mainframe, text="Confirmer", command = self.change_field).grid(column=0, row=4, sticky =(W,E,N,S))
        self.skip_field_btn = ttk.Button(mainframe, text="Ignorer", command= self.skip_field).grid(column=1, row=4, sticky=(W, E, N, S))

        ## Rangée 5
        self.correction = StringVar()
        self.correction_entry = ttk.Entry(mainframe, textvariable = self.correction, width=60)
        self.correction_entry.grid(column=0, row = 5, sticky=(N,S), columnspan=2)

        ## Rangée 6
        self.output_btn = ttk.Button(mainframe, text='Exporter résultat en pdf', command=self.output)
        self.output_btn.grid(column=0, row=6, sticky=(N,E,W), columnspan=3)

        ## Rangée 7
        #### Menu des options
        self.option_frame = ttk.Frame(mainframe, width= 300, height = 150, borderwidth=2, relief="solid", padding="1 1 4 4")
        # Titre de la section
        self.option_title = ttk.Label(self.option_frame, text="Options", font=title_font).grid(row=0, column=0, columnspan=3, sticky=(E,W))
        # Entrée facteur agrandissement avec validation de la valeur entrée
        check_num_wrapper = self.option_frame.register(check_num)
        self.scale_label = ttk.Label(self.option_frame, text = "Facteur d'agrandissement").grid(row=1, column=0, sticky=E)
        self.scale_entry = ttk.Entry(self.option_frame, textvariable=self.scale_factor, validate='key',
                                     validatecommand=(check_num_wrapper, '%P')).grid(row=1, column=1, sticky = W)

        # Entrée de la valeur du seuil de confiance pour accepter les mots
        self.conf_label = ttk.Label(self.option_frame, text="Seuil de confiance (%)").grid(row=2, column=0, sticky=(E,N))
        check_percent_wrapper = self.option_frame.register(check_percent)
        self.conf_threshold_entry = ttk.Entry(self.option_frame, textvariable=self.conf_threshold, validate='key',
                                              validatecommand=(check_percent_wrapper, '%P')).grid(row=2, column=1, sticky=(W,N))

        # Bouton pour activer le flou qui sert a enlever le bruit de l'image
        self.denoise_label = ttk.Label(self.option_frame, text = "Force du débruitage").grid(row=3, column=0, sticky = (E,N))

        self.denoise_entry = ttk.Entry(self.option_frame, text=self.denoise_factor, validate='key',
                                       validatecommand=(check_num_wrapper, '%P')).grid(row=3, column=1, sticky=(N,W))

        # Bouton type seuil binairisation
        self.threshold_label = ttk.Label(self.option_frame, text= "Binairisation adaptative").grid(row=4, column=0, sticky = (N,E))
        self.threshold_btn = ttk.Checkbutton(self.option_frame, command=self.load_reader(), variable=self.adapt_threshold,
                                             onvalue=True, offvalue=False)
        self.threshold_btn.grid(row=4, column=1,sticky=(N, W))

        # Boutons des langues
        self.lang_label = ttk.Label(self.option_frame, text="Langue :").grid(row=1, column=2, columnspan=2, sticky=S)
        self.fra_btn = ttk.Radiobutton(self.option_frame, text="Français", variable=self.lang, value = "fra").grid(row=2, column=2, sticky=(N,W))
        self.frh_btn = ttk.Radiobutton(self.option_frame, text= "Français Manuscrit", variable=self.lang, value= "frh").grid(row=3, column=2, sticky=(N,W))
        self.eng_btn = ttk.Radiobutton(self.option_frame, text= "Anglais", variable=self.lang, value = "eng").grid(row=4, column=2, sticky=(N,W))
        self.other_btn = ttk.Radiobutton(self.option_frame, text = "Autre :", variable=self.lang, value=self.other_lang.get())
        self.other_btn.grid(row=5, column=2, sticky=(N,E,W))
        self.lang_entry = ttk.Entry(self.option_frame, textvariable= self.other_lang).grid(row=5, column=3, sticky = (N,W))

        # Place le menu d'options dans la fenêtre
        self.option_frame.grid(column=0, row=7, sticky=(E, N), columnspan=2)

        # Bouton sortie
        self.exit_btn = ttk.Button(mainframe, text="Quitter", command=self.exit).grid(column=2, row=7, sticky=(W, N))

        ## Ajustement finaux de la fenêtre
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Ajustement des poids
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        mainframe.columnconfigure(0, weight=2)
        mainframe.columnconfigure(1, weight=2)
        mainframe.columnconfigure(2, weight=2)
        mainframe.columnconfigure(3, weight=1)
        mainframe.rowconfigure(3, weight=2)
        mainframe.rowconfigure(4, weight=1)
        mainframe.rowconfigure(5, weight=2)
        mainframe.rowconfigure(6, weight=1)
        mainframe.rowconfigure(7, weight=3)

    ### Méthodes des widgets
    def add_empty(self, *args):
        # Demande d'entrer le fichier de formulaire vide
        self.form = askopenfilename()
        # On affiche comme confirmation le nom du fichier seulement
        self.form_name_display.set(self.form_name_display.get()+self.form.split('/')[-1]+"\n")
        try:
            # On lit le formulaire avec la lecture de caractère et on garde en mémoire le résultat
            form_img = self.reader.read_image(self.form)
            scale_form = self.reader.scaling(form_img)
            clean_form = self.reader.preprocess(scale_form)
            self.form_data = self.reader.convert_to_dic(clean_form)
            self.form_bank[self.form] = self.form_data
            # Si on a déjà une image en mémoire on reéssaye d'identifier le formulaire
            if self.clean_img is not None:
                # On essaye d'identifier si l'image ressemble à un formulaire connu
                self.form = self.identify_form(self.clean_img)
        except  Exception as err:
            messagebox.showerror("Erreur", f"Erreur ajout image | {err.__class__.__name__} :  {err}")

    def add_image(self, *args):
        # Demande d'entrer le fichier de l'image a numériser
        self.file = askopenfilename()
        # On affiche comme confirmation le nom du fichier seulement
        self.filename_display.set(self.file.split('/')[-1])
        try:
            # On ouvre et fait la lecture de l'image
            image = self.reader.read_image(self.file)
            #image = self.reader.deskew(image)
            scale_img = self.reader.scaling(image)
            self.clean_img = self.reader.preprocess(scale_img)
            self.img_data = self.reader.convert_to_dic(self.clean_img)
            # On essaye d'identifier si l'image ressemble à un formulaire connu
            self.form = self.identify_form(self.clean_img)
            # Si on a un formulaire vide, on enlève le texte déjà présent avant la correction de l'image
            if len(self.form) > 0:
                self.isolate_filled_fields()
            # On obtient le premier à corriger et on ajuste l'affichage
            self.get_next_correction()
        except  Exception as err:
            messagebox.showerror("Erreur", f"Erreur ajout image | {err.__class__.__name__} :  {err}")

    def change_field(self):
        try:
            self.get_next_correction(self.review_index.get(), self.correction.get())
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur affichage prochain champ | {err.__class__.__name__} :  {err}")

    def skip_field(self):
        try:
            # On enlève le champ qui n'est pas pertinent et on ajuste l'index
            self.remove_from_img_data(self.review_index.get())
            self.review_index.set(self.review_index.get()-1)
            # On va chercher le prochain mot et on l'affiche
            self.get_next_correction(self.review_index.get())
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur affichage prochain champ | {err.__class__.__name__} :  {err}")

    def exit(self):
        app_root.destroy()

    def output(self):
        try:
            output_file = asksaveasfilename()
            handler = PdfHandler(float(self.scale_factor.get()))
            pdf_page_shape = get_page_shape(self.form, 0)
            handler.build_text_layer(self.img_data, r"temp\read_pdf", pdf_page_shape)
            handler.create_output(r"temp\read_pdf", self.form, output_file)
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur création du PDF de sortie | {err.__class__.__name__} :  {err}")

    ### Autres méthodes
    def get_next_correction(self, index=0, correction=None):
        self.img_data, review_index, review_text = self.reader.correction(self.img_data, correction_index=index, correction_text=correction)
        if review_index == -1:
            review_text = "Fin du document"
        self.review_index.set(review_index)
        self.review_text.set(review_text)
        self.update_image(review_index)
        self.update_stats()
        # On oublie pas de vider la case d'entrée de texte
        self.correction_entry.delete(0, 'end')

    def isolate_filled_fields(self):
        # On veut seulement garder le texte qui n'est pas déjà sur le formulaire vide
        img_boxes = len(self.img_data['text'])
        form_boxes = len(self.form_data['text'])
        duplicate_words = []
        # On itère sur le texte de l'image qu'on numérise
        for i in range(img_boxes):
            img_word = self.img_data['text'][i]
            if img_word == '':
                continue
            # On obtient la position relative du mot dans la page
            x_ratio_img, y_ratio_img = get_coords(self.img_data, i, (1.0,1.0))   # Pose que la page est de taille 1x1 pour obtenir les ratios
            # On compare ce mot à tous ceux dans le formulaire vide
            for j in range(form_boxes):
                form_word = self.form_data['text'][j]
                if form_word.lower() == img_word.lower():
                    x_ratio_form,y_ratio_form = get_coords(self.form_data, j, (1.0,1.0))
                    # On regarde si les mots sont un peu près dans la même région de l'image.
                    # Si leur coordonnées sont moins de 10% de la valeur de l'autre, on conclue que c'est le même mot
                    if math.isclose(x_ratio_img, x_ratio_form, rel_tol=.1) and math.isclose(y_ratio_img, y_ratio_form, rel_tol=.1) :
                        duplicate_words.append(i)
                        break
        # Une fois qu'on fini la recherche on enlève ceux présents sur le formulaire vide,
        # on parcours à partir de la fin pour ne pas que ce qu'on efface change la position des autres mots à effacer
        for i in reversed(duplicate_words):
            self.remove_from_img_data(i)

    def load_reader(self):
        self.reader = Reader(lang=self.lang.get(), scale_factor=float(self.scale_factor.get()),
                             adapt_thresh=self.adapt_threshold.get(), blur_sigma=float(self.denoise_factor.get()),
                             conf_threshold=self.conf_threshold.get())

    def update_stats(self):
        try :
            if len(self.img_data) == 0:
                return
            else:
                nb_boxes = len(self.img_data['text'])
                confident_boxes = []
                text_preview = ''
                form_text = ""
                if self.form != "":
                    form_text = f"Formulaire identifié : {self.form.split('/')[-1]} \n\n"
                for i in range(nb_boxes) :
                    if int(self.img_data['conf'][i]) > self.conf_threshold.get():
                        confident_boxes.append(i)
                        if len(confident_boxes) < 30 :
                            text_preview += self.img_data['text'][i] + " "
                self.stat_text.set(f'{form_text}Nombre de boîtes : {nb_boxes} \nConfiance > '
                                   f'{self.conf_threshold.get()}% : {len(confident_boxes)}' f'\n\nAperçu du texte : \n{text_preview}')
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur affichage statistiques  | {err.__class__.__name__} :  {err}")

    def update_image(self, index):
        try :
            if index == -1:
                return
            # Va chercher l'image complète et les coordonnées de la boîte voulue
            image = self.reader.read_image(self.file)
            image = self.reader.deskew(image)
            image = self.reader.scaling(image)
            top = self.img_data['top'][index]
            left = self.img_data['left'][index]
            width = self.img_data['width'][index]
            height = self.img_data['height'][index]
            # Pour selectionner les pixels dans la matrice numpy, c'est : rangée, colonne
            # On va afficher une image plus grande de 10 pixels dans chaque direction pour donner du contexte
            box_image = image[top-10:top+height+10, left-10:left+width+10]
            self.image_display.config(width=box_image.shape[1], height=box_image.shape[0])
            box_corrected = cv2.cvtColor(box_image, cv2.COLOR_BGR2RGB)
            self.box_photo = ImageTk.PhotoImage(image=Image.fromarray(box_corrected))
            # On crée l'affichage de l'image si c'est la première fois, sinon on modifie et les 2 seulement si l'image a été bien crée
            if self.image_id is None and self.box_photo is not None:
                self.image_id = self.image_display.create_image(0, 0, image=self.box_photo, anchor='nw')
            elif self.box_photo is not None:
                self.image_display.itemconfig(self.image_id, image=self.box_photo)
        except Exception as err:
            messagebox.showerror("Erreur", f"Erreur affichage image  | {err.__class__.__name__} :  {err}")

    def remove_from_img_data(self, i):
        self.img_data['level'].pop(i)
        self.img_data['page_num'].pop(i)
        self.img_data['block_num'].pop(i)
        self.img_data['par_num'].pop(i)
        self.img_data['line_num'].pop(i)
        self.img_data['word_num'].pop(i)
        self.img_data['left'].pop(i)
        self.img_data['top'].pop(i)
        self.img_data['width'].pop(i)
        self.img_data['height'].pop(i)
        self.img_data['conf'].pop(i)
        self.img_data['text'].pop(i)

    def identify_form(self, image):
        match_score = dict()
        for file in self.form_bank :
            form_img = self.reader.read_image(file)
            form_clean = self.reader.preprocess(form_img)
            # Les dimensions doivent être inversé par rapport au retour de shape pour la fonction scaling
            form_dimension = form_clean.shape[1], form_clean.shape[0]
            # On ajuste l'image a la taille du formulaire
            scaled_img = cv2.resize(image, form_dimension, cv2.INTER_CUBIC)
            match_array = cv2.matchTemplate(scaled_img, form_clean, cv2.TM_CCOEFF)  # TM_CCOEFF = Template Matching Correlation Coefficient
            # Normalement si les images sont de la même grandeur on obtient une seule valeur mais on prend le max au cas ou ce n'était pas le cas
            match_score[file] = (max(match_array))
        if len(match_score) == 0:
            return ""
        else :
            # On retourne le nom du fichier (clé du dict) associée à la valeur maximale du score de correspondance
            return max(match_score, key=match_score.get)

def check_num(newval):
    # Quand utilisateur efface, on recoit "". On veut donc le permettre en tout temps
    if newval == "":
        return True
    else:
        # On accepte le caractère si c'est un chiffre ou si c'est un point et que ce n'est pas le premier caractère. Max de 4 caractère
        return re.match('^[0-9]+[0-9.]*$', newval) is not None and len(newval) <=4

def check_percent(newval):
    if newval == "":
        return True
    # On accepte le caractère si c'est un chiffre uniquement (pas décimales) et si cela donne un total maximum de 100
    elif re.match('^[0-9]+$', newval) is not None :
        return int(newval) <= 100
    else:
        return False

app_root = Tk()
MainWindow(app_root)
if __name__ == '__main__':
    app_root.mainloop()