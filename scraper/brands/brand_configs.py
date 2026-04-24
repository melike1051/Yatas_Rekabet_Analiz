BRAND_CONFIGS = {
    "istikbal": {
        "base_url": "https://www.istikbal.com.tr",
        "category_sources": [
            {
                "category_name": "Yemek Odasi",
                "url": "https://www.istikbal.com.tr/kategori/yemek-odasi-takimlari",
            }
        ],
        "campaigns_url": "https://www.istikbal.com.tr/kampanyalar",
        "selectors": {
            "product_card": ".showcase",
            "product_name": "h3",
            "product_price": ".showcase-price-new",
            "original_price": ".showcase-price-old",
            "stock_label": ".stock-status",
            "promotion_badge": ".campaign-badge",
            "sku": "[data-sku]",
            "product_link": "a.view-button",
        },
    },
    "bellona": {
        "base_url": "https://www.bellona.com.tr",
        "category_sources": [
            {
                "category_name": "Yemek Odasi",
                "url": "https://www.bellona.com.tr/kategori/yemek-odasi-takimi",
            },
            {
                "category_name": "Yemek Odasi",
                "url": "https://www.bellona.com.tr/kategori/yemek-odasi?tp=6",
            }
        ],
        "campaigns_url": "https://www.bellona.com.tr/kampanyalar",
        "selectors": {
            "product_card": ".product-item",
            "product_name": ".product-item__title",
            "product_price": ".product-item__price-current",
            "original_price": ".product-item__price-old",
            "stock_label": ".product-item__stock",
            "promotion_badge": ".product-item__badge",
            "sku": "[data-product-sku]",
            "product_link": "a",
        },
    },
    "dogtas": {
        "base_url": "https://www.dogtas.com",
        "category_sources": [
            {
                "category_name": "Yemek Odasi",
                "url": "https://www.dogtas.com/yemek-odasi",
            }
        ],
        "campaigns_url": "https://www.dogtas.com/kampanyalar",
        "selectors": {
            "product_card": ".card-product",
            "product_name": ".c-p-i-link",
            "product_price": ".sale-price",
            "original_price": ".new-sale-price",
            "stock_label": ".products__stock",
            "promotion_badge": ".products__badge",
            "sku": "[data-sku]",
            "product_link": ".c-p-i-link",
        },
    },
}
