# USAGE
# python verify_card.py --template templates/CDC_card_template_01.png --image scans/valid/covid_01.JPEG

import argparse
import re
from collections import namedtuple

import cv2
import imutils
import numpy as np
import pytesseract
from pyimagesearch.alignment import align_images

# try:
#     from PIL import Image
# except ImportError:
#     import Image

# create a named tuple which we can use to create locations of the
# input document which we wish to OCR
OCRLocation = namedtuple("OCRLocation", ["id", "bbox", "filter_keywords"])

# define the locations of each area of the document we wish to OCR
OCR_LOCATIONS = [
    OCRLocation("title", (0, 0, 1487, 160), [""]),
    OCRLocation("last_name", (23, 427, 905, 161), ["last", "name"]),
    OCRLocation("first_name", (919, 387, 900, 205), ["first", "name"]),
    OCRLocation("middle_initial", (1814, 387, 177, 189), ["MI"]),
    OCRLocation("dob", (23, 583, 749, 113), ["date", "of", "birth"])
]


# def perform_OCR():
# 	# get the regions of interest
# 	for loc in OCR_LOCATIONS:
# 		(x, y, w, h) = loc.bbox
# 		roi = aligned[y:y + h, x:x + w]

# 		# cv2.imwrite("output/" +  loc.id + ".jpg", roi)
# 		cv2.imwrite(f"output/{args['tag']}_field_{loc.id}.jpg", roi)

# 		# OCR the ROI using Tesseract
# 		rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
# 		text = pytesseract.image_to_string(rgb)
# 		print(f'{loc.id}:')
# 		print(text)

def read_title(aligned, fileTag='', debug=False) -> str:
    loc = OCR_LOCATIONS[0]

    # get title ROI
    (x, y, w, h) = loc.bbox
    roi = aligned[y:y + h, x:x + w]

    # show ROI
    if debug:
        # cv2.imwrite("output/" +  loc.id + ".jpg", roi)
        cv2.imwrite(f"output/{args['tag']}_field_{loc.id}.jpg", roi)

    # OCR the ROI using Tesseract
    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    text = pytesseract.image_to_string(rgb)

    return text


def logo_template_match(aligned, template_img, debug=True):
    """
    Returns the top-left 2D coordinate of the template match.
    """

    # first convert to grayscale
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    logo_template_gray = cv2.cvtColor(logo_template, cv2.COLOR_BGR2GRAY)
    logo_template_h = logo_template_gray.shape[0]
    logo_template_w = logo_template_gray.shape[1]

    # perform Zero-normalized cross-correlation template match
    result = cv2.matchTemplate(aligned_gray, logo_template_gray, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)  # highest value is the best match

    if debug:
        # get the ROI coordinates for the match
        roi_x0 = min(aligned_gray.shape[1], max(0, max_loc[0]))
        roi_y0 = min(aligned_gray.shape[0], max(0, max_loc[1]))
        roi_x1 = min(aligned_gray.shape[1], max(0, max_loc[0] + logo_template_w))
        roi_y1 = min(aligned_gray.shape[0], max(0, max_loc[1] + logo_template_h))

        # visualize the match next to the template
        aligned_roi = aligned_gray[roi_y0:roi_y1, roi_x0:roi_x1]
        tm_stacked = np.hstack([aligned_roi, logo_template_gray])
        cv2.imwrite(f"output/{args['tag']}_TM.jpg", tm_stacked)

    return max_loc


def verify_card(RANSAC_inliers, title, TM_loc) -> bool:
    # require a minimum number of inliers during the homography estimation
    if RANSAC_inliers < 11:
        print("failed RANSAC inlier verification!")
        return False

    # verify title with regex (allowing for variable amounts of whitespace)
    expectedTitleRegex = re.compile(r'(COVID\s*-\s*1\s*9\s*Vaccination\s*Record\s*Card)', re.DOTALL)
    match = expectedTitleRegex.search(title)
    if match is None:
        print(f"failed title verification! title: {title}")
        return False

    # verify the CDC logo is near the top right corner
    if TM_loc[0] < 1470 or TM_loc[1] > 10:
        print("failed CDC logo check. should be in top right!")
        return False

    return True


def visualize_aligned(aligned, template, fileTag=''):
    # resize both the aligned and template images so we can easily
    # visualize them on our screen
    aligned = imutils.resize(aligned, width=700)
    template = imutils.resize(template, width=700)

    # our first output visualization of the image alignment will be a
    # side-by-side comparison of the output aligned image and the
    # template
    stacked = np.hstack([aligned, template])

    # our second image alignment visualization will be *overlaying* the
    # aligned image on the template, that way we can obtain an idea of
    # how good our image alignment is
    overlay = template.copy()
    output = aligned.copy()
    cv2.addWeighted(overlay, 0.5, output, 0.5, 0, output)

    # show the two output image alignment visualizations
    # cv2.imshow("Image Alignment Stacked", stacked)
    # cv2.imshow("Image Alignment Overlay", output)
    # cv2.waitKey(0)
    cv2.imwrite(f"output/{args['tag']}_stacked.jpg", stacked)
    cv2.imwrite(f"output/{args['tag']}_overlay.jpg", output)


if __name__ == "__main__":

    # parse arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
                    help="path to input image that we'll align to template")
    ap.add_argument("-t", "--template", required=True,
                    help="path to input template image")
    ap.add_argument("--tag", required=False,
                    help="prefix for output files")
    args = vars(ap.parse_args())

    # load the input image and template from disk
    print("[INFO] loading images...")
    image = cv2.imread(args["image"])
    template = cv2.imread(args["template"])
    logo_template = cv2.imread('templates/cdc_logo_template.png')

    # align the images
    print("[INFO] aligning images...")
    aligned, RANSAC_inliers = align_images(image, template, args["tag"], debug=True)

    # visualize aligned images
    visualize_aligned(aligned, template, fileTag=args["tag"])

    # perform OCR on the aligned image
    # perform_OCR()
    title = read_title(aligned, fileTag=args["tag"], debug=True)

    # perform logo template match
    max_loc = logo_template_match(aligned, logo_template, debug=True)

    # verify it is a valid vaccination card
    verified = verify_card(RANSAC_inliers, title, max_loc)
    if verified:
        print("Valid vaccination card detected!")
    else:
        print("Invalid vaccination card detected!")
