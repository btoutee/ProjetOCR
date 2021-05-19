import cv2
import numpy as np
from matplotlib import pyplot as plt
import pdf2image
import pytesseract
import os
from pytesseract import Output

class Reader:
    def __init__(self, lang="fra",scale_factor=1.2, blur_size=5, blur_sigma=40, adapt_thresh=False,
                 save_folder="images", conf_threshold=80):
        self.scale_factor = scale_factor
        self.blur_size = blur_size
        self.blur_sigma = blur_sigma
        self.adapt_threshold = adapt_thresh
        self.lang = lang
        self.save_folder = save_folder
        self.conf_thresh = conf_threshold

    def correction(self, img_data, correction_index=0, correction_text=None):
        nb_boxes = len(img_data['text'])
        # Si une correction ou confirmation a été faite, on l'applique et change la confiance du champ à 100%
        if correction_text is not None:
            img_data['conf'][correction_index] = 100
            # Un texte "" est une confirmation : la valeur déjà présente est correcte donc on ne la change pas
            if correction_text != "":
                img_data['text'][correction_index] = correction_text

        # Va chercher le prochain champ à corriger
        for i in range(correction_index+1, nb_boxes):
            # On corrige seulement les boites qui ont un score de confiance de moins de 80%
            if int(img_data['conf'][i]) < self.conf_thresh and img_data['text'][i] != '':
                return img_data, i, img_data['text'][i]
        return img_data, -1, ''

    def convert_to_dic(self, image):
        # C'est ici que le réseau neuronaux de Tesseract détecte le texte à partir de l'image
        data = pytesseract.image_to_data(image,lang=self.lang, output_type=Output.DICT)
        # En plus de toutes les données sur le texte on rajoute des informations sur la page
        data['page_height'], data['page_width'] = np.shape(image)[:2]
        return data

    def preprocess(self, image, do_greyscale=True, do_blur=True, do_threshold=True):
        if do_greyscale:
            image = self.greyscale(image)
        if do_blur:
            image = self.blurring(image, self.blur_size, self.blur_sigma)
        if do_threshold:
            image = self.thresholding(image)
        return image

    def scaling(self, image):
        return cv2.resize(image, None, fx=self.scale_factor, fy=self.scale_factor, interpolation=cv2.INTER_CUBIC)

    def greyscale(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def blurring(self, image, filter_size, sigma_size):
        # Flou bien fait permet d'effacer les saletés et bruit sans perdre le texte bien défini
        return cv2.bilateralFilter(image, filter_size, sigma_size, sigma_size)

    def thresholding(self, image):
        if self.adapt_threshold:    # Si l'utilisateur veut utiliser la binairisation adaptative (qui marche mieux pour éclairage inégal)
            return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
        else :                      # sinon un utilise un seuil global (marche très bien pour éclairage égal)
            return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    def pdf_to_image(self, pdf_path, output_file, save_folder):
        return pdf2image.convert_from_path(pdf_path, fmt="jpeg",
                                           output_folder=save_folder, output_file="preimage", paths_only=True)

    def read_image(self, path):
        extension = os.path.splitext(path)[-1].lower()
        if extension == ".pdf":
            target_file = path[:-3]+"jpg"
            # recoit une liste des path pour chaque page du pdf
            image_path_list = self.pdf_to_image(path, target_file, self.save_folder)
            # La gestion de plusieurs pages n'a pas été implémentée alors retourne seulement première page
            path = image_path_list[0]
        return cv2.imread(path)

    def image_to_text(self, image, save_path):
        with open(save_path, "w") as text_file:
            text_file.write(pytesseract.image_to_string(image, lang=self.lang))

    def deskew(self, image, max_skew=10):  # Pour corrigier l'orientation de l'image
        # Traite image pour avoir le background noir(0) et le texte écrit blanc
        height, width = image.shape[:2]
        image_gray = self.greyscale(image)
        image_gray = cv2.bitwise_not(image_gray)
        thresh = self.thresholding(image_gray)
        # Fais le rectangle le plus petit contenant tous les pixels non nuls et trouve son angle
        coords = np.column_stack(np.where(thresh>0))
        angle = cv2.minAreaRect(coords)[-1]
        # Corrige valeur angle pour pouvoir faire la rotation
        if angle < -45 :
            angle = -(90+angle)
        else :
            angle =-angle
        center = (width//2, height//2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        # Ajuste taille image pour garder les dimensions originales
        rotated = cv2.warpAffine(image, M, (width, height),
                                 flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def show_image(self, image):
        # Pour donner apercu image (principalement pour debugging du traitement d'image)
        plt.imshow(image, cmap='gray', interpolation='bicubic')
        plt.xticks([]), plt.yticks([])  # cache les échelles X et Y
        plt.show()
        k = cv2.waitKey(0) & 0xFF
        if k == 27:  # attends touche ESC pour quitter
            cv2.destroyAllWindows()
        elif k == ord('s'):  # si appuie sur 's', sauvegarde image
            cv2.imwrite('result/imageGrey.png', image)
            cv2.destroyAllWindows()

    def detect_boxes(self, image, img_data):
        # Ajoute des boîtes visuelle sur image à partir du texte detecté par Tesseract (pour débuggage lecture caractère)
        nb_boxes = len(img_data['text']) #nombre de boites
        for i in range(nb_boxes):
            if int(img_data['conf'][i]) > 5:  # on affiche seulement les boites qui ont un confiance de 5%+
                (x,y,w,h) = (img_data['left'][i], img_data['top'][i], img_data['width'][i], img_data['height'][i])
                image = cv2.rectangle(image, (x,y), (x+w, y+h), (0, 255, 0), 2) # ajoute boite rouge a l'image
                print(img_data['text'][i])
        return image