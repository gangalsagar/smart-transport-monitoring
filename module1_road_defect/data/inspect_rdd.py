from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter


ANNOTATIONS_DIR = Path(
    "module1_road_defect/data/raw/train/annotations/xmls"
)


class_counts = Counter()

images_with_d40 = 0
images_without_d40 = 0

d40_objects_per_image = []


xml_files = list(ANNOTATIONS_DIR.glob("*.xml"))

for xml_file in xml_files:

    tree = ET.parse(xml_file)
    root = tree.getroot()

    objects = root.findall("object")

    image_classes = []

    for obj in objects:
        name = obj.findtext("name")

        if name:
            class_counts[name] += 1
            image_classes.append(name)

    d40_count = image_classes.count("D40")

    if d40_count > 0:
        images_with_d40 += 1
        d40_objects_per_image.append(d40_count)
    else:
        images_without_d40 += 1


print("\n========== RDD2022 INSPECTION ==========")

print(f"Total images/annotations : {len(xml_files)}")

print(f"Images WITH D40          : {images_with_d40}")

print(f"Images WITHOUT D40       : {images_without_d40}")

print(f"Total D40 objects        : {class_counts['D40']}")

print("\nClass distribution:")

for class_name, count in class_counts.most_common():
    print(f"  {class_name}: {count}")

if d40_objects_per_image:

    average = sum(d40_objects_per_image) / len(d40_objects_per_image)

    print("\nD40 statistics:")

    print(f"  Average D40/image : {average:.2f}")

    print(f"  Minimum D40/image : {min(d40_objects_per_image)}")

    print(f"  Maximum D40/image : {max(d40_objects_per_image)}")