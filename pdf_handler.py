import PyPDF2
from reportlab.pdfgen import canvas
import os
import shutil
import math

class PdfHandler:
    def __init__(self, scale_factor=1.0):
        self.scale_factor = float(scale_factor)

    def create_output(self, read_pdf_path, form_path, output_path):
        # S'il n'y a pas de formulaire vide avec lequel fusionné, le texte lu par Tesseract est notre output
        if form_path == "":
            shutil.move(read_pdf_path, self.path_as_pdf(output_path))
            #os.rename(read_pdf_path, self.path_as_pdf(output_path))
        else:
            with open(form_path, 'rb') as form_file, open(read_pdf_path, 'rb') as read_file:  # suppose que les 2 sont des path
                form, read = (PyPDF2.PdfFileReader(x) for x in (form_file, read_file))
                outpdf = PyPDF2.PdfFileWriter()
                # On fusionne les pages du formulaire vide et de la couche de texte lu par tesseract
                for (page1, page2) in zip(form.pages, read.pages):
                    page1.mergePage(page2)
                    outpdf.addPage(page1)
                nb_page_form, nb_page_read = len(form.pages), len(read.pages)
                # Gestion si le nombre de page n'est pas égal
                if nb_page_form != nb_page_read:
                    for page in (read.pages[nb_page_form:] if nb_page_form < nb_page_read else form.pages[nb_page_read:]):
                        outpdf.addPage(page)
                with open(self.path_as_pdf(output_path), 'wb') as out_file:
                    outpdf.write(out_file)

    def build_text_layer(self, img_data, output_file, pdf_page_shape):
        # On génère un pdf contenant juste une couche de texte correspondant aux champs manuscrit lus
        canv = canvas.Canvas(output_file)
        nb_boxes = len(img_data['text'])
        for i in range(nb_boxes) :
            if img_data['text'][i] != "":
                # On veut placer le texte au bon endroit sur la page mais les pdf n'ont pas les mêmes unités ni même point origine
                posx, posy = get_coords(img_data, i, pdf_page_shape)
                # Approxime la taille de la police en proportion par raport à la taille de la page
                height_ratio = img_data['height'][i] / img_data['page_height']
                font_size = math.floor(height_ratio*pdf_page_shape[1]/2)*2  # On arrondi vers le bas puisqu'on priorise la lisibilité
                canv.setFontSize(font_size)
                canv.drawString(posx,posy, img_data['text'][i])
        canv.showPage()
        canv.save()

    # Makes sure the output file has the right extension
    def path_as_pdf(self, path):
        root_ext = os.path.splitext(path)
        extension = root_ext[1].lower()
        root = root_ext[0]
        if extension == ".pdf":
            return path
        else:
            return root+".pdf"


# On veut la taille du pdf dans le standard 72pts/pouces pour les manipuler correctement
def get_page_shape(form_path="", page_nbr=0):
    # Si on a pas de formulaire comme exemple, on prend la taille A4 par défaut
    if form_path == "":
        return 595.27, 841.89
    with open(form_path, "rb") as form_file:
        form = PyPDF2.PdfFileReader(form_file)
        # MediaBox donne les coordonnées du rectangle qui inclue la page au complet, on prend largeur et hauteur
        return form.getPage(page_nbr).mediaBox[2], form.getPage(page_nbr).mediaBox[3]

# Les PDF ont l'origine en bas à gauche de l'image alors que Tesseract l'a en haut à gauche, donc il faut convertir
def get_coords(img_data, i, pdf_shape):
    # Comme le formulaire et l'image n'ont pas les mêmes résolutions, on place le texte en fonction du placement relatif a la taille de la page
    xratio = img_data['left'][i]/img_data['page_width']
    # L'origine en image est le coin supérieur gauche alors qu'en pdf c'est inférieur gauche, on change de coin comme origine
    # De plus, l'origine de la boite d'un mot est en haut a gauche alors que le texte d'un pdf a une origine en bas à gauche
    yratio = (img_data['page_height']-img_data['top'][i]-img_data['height'][i])/img_data['page_height']
    rescaled_x = xratio*pdf_shape[0]
    rescaled_y = yratio*pdf_shape[1]
    return rescaled_x, rescaled_y
