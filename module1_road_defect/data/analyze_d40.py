from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter
import statistics


PROJECT_ROOT = Path(__file__).resolve().parents[2]

XML_DIR = (
    PROJECT_ROOT
    / "module1_road_defect"
    / "data"
    / "raw"
    / "train"
    / "annotations"
    / "xmls"
)


def main():

    print("=" * 60)
    print("RDD2022 D40 DATASET ANALYSIS")
    print("=" * 60)

    xml_files = list(XML_DIR.glob("*.xml"))

    print(f"\nXML files: {len(xml_files)}")

    d40_widths = []
    d40_heights = []
    d40_areas = []
    d40_area_percentages = []
    d40_per_image = []

    class_counts = Counter()

    image_widths = []
    image_heights = []

    for xml_file in xml_files:

        root = ET.parse(xml_file).getroot()

        size = root.find("size")

        if size is None:
            continue

        image_width = int(
            size.find("width").text
        )

        image_height = int(
            size.find("height").text
        )

        image_widths.append(image_width)
        image_heights.append(image_height)

        image_area = image_width * image_height

        current_d40 = 0

        for obj in root.findall("object"):

            name = obj.find("name").text.strip()

            class_counts[name] += 1

            if name != "D40":
                continue

            box = obj.find("bndbox")

            xmin = int(box.find("xmin").text)
            ymin = int(box.find("ymin").text)
            xmax = int(box.find("xmax").text)
            ymax = int(box.find("ymax").text)

            width = max(0, xmax - xmin)
            height = max(0, ymax - ymin)

            area = width * height

            percentage = (
                area / image_area
            ) * 100

            d40_widths.append(width)
            d40_heights.append(height)
            d40_areas.append(area)
            d40_area_percentages.append(percentage)

            current_d40 += 1

        d40_per_image.append(current_d40)

    # --------------------------------------------------------
    # Image statistics
    # --------------------------------------------------------

    print("\nIMAGE SIZE")
    print("-" * 60)

    print(
        "Width:",
        min(image_widths),
        "-",
        max(image_widths),
        "average:",
        round(statistics.mean(image_widths), 2)
    )

    print(
        "Height:",
        min(image_heights),
        "-",
        max(image_heights),
        "average:",
        round(statistics.mean(image_heights), 2)
    )

    # --------------------------------------------------------
    # Class distribution
    # --------------------------------------------------------

    print("\nCLASS DISTRIBUTION")
    print("-" * 60)

    for cls, count in class_counts.most_common():

        print(
            f"{cls:5s}: {count}"
        )

    # --------------------------------------------------------
    # D40 statistics
    # --------------------------------------------------------

    print("\nD40 OBJECT STATISTICS")
    print("-" * 60)

    print(
        "Total D40 boxes:",
        len(d40_widths)
    )

    print(
        "D40 boxes/image:",
        round(
            statistics.mean(d40_per_image),
            2
        )
    )

    print(
        "Minimum/image:",
        min(d40_per_image)
    )

    print(
        "Maximum/image:",
        max(d40_per_image)
    )

    print(
        "\nBounding-box width:"
    )

    print(
        "  Min:",
        min(d40_widths)
    )

    print(
        "  Max:",
        max(d40_widths)
    )

    print(
        "  Mean:",
        round(
            statistics.mean(d40_widths),
            2
        )
    )

    print(
        "\nBounding-box height:"
    )

    print(
        "  Min:",
        min(d40_heights)
    )

    print(
        "  Max:",
        max(d40_heights)
    )

    print(
        "  Mean:",
        round(
            statistics.mean(d40_heights),
            2
        )
    )

    print(
        "\nBounding-box area percentage:"
    )

    print(
        "  Min:",
        round(
            min(d40_area_percentages),
            4
        ),
        "%"
    )

    print(
        "  Max:",
        round(
            max(d40_area_percentages),
            4
        ),
        "%"
    )

    print(
        "  Mean:",
        round(
            statistics.mean(d40_area_percentages),
            4
        ),
        "%"
    )

    # --------------------------------------------------------
    # Small objects
    # --------------------------------------------------------

    print("\nSMALL OBJECT ANALYSIS")
    print("-" * 60)

    image_area = 720 * 720

    thresholds = [
        1,
        2,
        5,
        10
    ]

    for threshold in thresholds:

        count = sum(
            1
            for area in d40_area_percentages
            if area < threshold
        )

        percentage = (
            count / len(d40_area_percentages)
        ) * 100

        print(
            f"D40 < {threshold:2d}% image area:"
            f" {count:4d} boxes"
            f" ({percentage:.2f}%)"
        )

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()