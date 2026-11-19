DROP SCHEMA IF EXISTS smartphones CASCADE;
CREATE SCHEMA smartphones;

-- СПРАВОЧНИКИ 
CREATE TABLE smartphones.brand        (brand_id        SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.color        (color_id        SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.os           (os_id           SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.form_factor  (form_factor_id  SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.panel_type   (panel_type_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.notch_type   (notch_type_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.screen_glass (screen_glass_id SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.material     (material_id     SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.ram_type     (ram_type_id     SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.battery_type (battery_type_id SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.flash_type   (flash_type_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.gpu_vendor   (gpu_vendor_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.cpu_vendor   (cpu_vendor_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE smartphones.cpu_family   (cpu_family_id   SMALLINT PRIMARY KEY, name TEXT NOT NULL UNIQUE);

CREATE TABLE smartphones.video_res (
    video_res_id SMALLINT PRIMARY KEY,
    name         TEXT     NOT NULL UNIQUE,
    quality_rank SMALLINT NOT NULL UNIQUE -- порядок качества: 1 = HD ... 5 = 8K
);

-- Процессор: вендор и линейка однозначно определяются моделью чипа
CREATE TABLE smartphones.cpu (
    cpu_id        SMALLINT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    cpu_vendor_id SMALLINT REFERENCES smartphones.cpu_vendor (cpu_vendor_id),
    cpu_family_id SMALLINT REFERENCES smartphones.cpu_family (cpu_family_id)
);

-- Модель телефона: бренд + название
CREATE TABLE smartphones.phone_model (
    model_id SMALLINT PRIMARY KEY,
    brand_id SMALLINT NOT NULL REFERENCES smartphones.brand (brand_id),
    name     TEXT     NOT NULL,
    UNIQUE (brand_id, name)
);

-- Товар = карточка на DNS
CREATE TABLE smartphones.phone (
    phone_id       INTEGER  PRIMARY KEY,
    model_id       SMALLINT NOT NULL REFERENCES smartphones.phone_model (model_id),
    color_id       SMALLINT REFERENCES smartphones.color (color_id),
    memory_gb      SMALLINT NOT NULL CHECK (memory_gb > 0),  
    ram_gb         SMALLINT CHECK (ram_gb > 0),
    price          INTEGER  NOT NULL CHECK (price > 0),    
    useful_life    SMALLINT,                                  
    year_release   SMALLINT,
    form_factor_id SMALLINT REFERENCES smartphones.form_factor (form_factor_id),
    os_id          SMALLINT REFERENCES smartphones.os (os_id)
);

-- ХАРАКТЕРИСТИКИ (связь 1:1 с phone, ключ = phone_id)
CREATE TABLE smartphones.phone_display (
    phone_id         INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    diag             NUMERIC(3,1),          
    screen_w         SMALLINT,             
    screen_h         SMALLINT,
    brightness_nits  SMALLINT,
    refresh_hz       SMALLINT,
    color_depth_bits SMALLINT,
    panel_type_id    SMALLINT REFERENCES smartphones.panel_type (panel_type_id),
    notch_type_id    SMALLINT REFERENCES smartphones.notch_type (notch_type_id),
    screen_glass_id  SMALLINT REFERENCES smartphones.screen_glass (screen_glass_id),
    curved_screen    BOOLEAN,
    bezelless        BOOLEAN
);

CREATE TABLE smartphones.phone_body (
    phone_id          INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    width_mm          NUMERIC(5,1),
    height_mm         NUMERIC(5,1),
    thickness_mm      NUMERIC(4,1),
    weight_g          NUMERIC(5,1),
    back_material_id  SMALLINT REFERENCES smartphones.material (material_id),
    frame_material_id SMALLINT REFERENCES smartphones.material (material_id),
    ip_dust           SMALLINT CHECK (ip_dust  BETWEEN 0 AND 6),
    ip_water          SMALLINT CHECK (ip_water BETWEEN 0 AND 9),
    rugged            BOOLEAN
);

CREATE TABLE smartphones.phone_performance (
    phone_id      INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    cpu_id        SMALLINT REFERENCES smartphones.cpu (cpu_id),
    cpu_cores     SMALLINT,
    process_nm    SMALLINT,
    cpu_ghz       NUMERIC(4,2),
    gpu_vendor_id SMALLINT REFERENCES smartphones.gpu_vendor (gpu_vendor_id),
    ram_type_id   SMALLINT REFERENCES smartphones.ram_type (ram_type_id),
    os_version    SMALLINT,
    is_gaming     BOOLEAN
);

CREATE TABLE smartphones.phone_camera_rear (
    phone_id       INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    rear_cams      SMALLINT,
    has_telephoto  BOOLEAN,
    has_periscope  BOOLEAN,
    has_ultrawide  BOOLEAN,
    has_macro      BOOLEAN,
    digital_zoom   SMALLINT,
    video_res_id   SMALLINT REFERENCES smartphones.video_res (video_res_id),
    flash_type_id  SMALLINT REFERENCES smartphones.flash_type (flash_type_id),
    ois            BOOLEAN,
    main_autofocus BOOLEAN,
    slow_motion    BOOLEAN
);

CREATE TABLE smartphones.phone_camera_front (
    phone_id        INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    front_autofocus BOOLEAN,
    front_flash     BOOLEAN,
    dual_front_cam  BOOLEAN
);

CREATE TABLE smartphones.phone_power (
    phone_id          INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    battery_mah       INTEGER,
    battery_type_id   SMALLINT REFERENCES smartphones.battery_type (battery_type_id),
    charger_in_box    BOOLEAN,
    charger_w_in_box  NUMERIC(5,1),      
    fast_charge       BOOLEAN,
    wired_charge_w    NUMERIC(5,1),      
    wireless_charge   BOOLEAN,
    wireless_charge_w NUMERIC(5,1),
    reverse_charge    BOOLEAN,
    reverse_wireless  BOOLEAN
);

CREATE TABLE smartphones.phone_connectivity (
    phone_id      INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    has_5g        BOOLEAN,
    lte_advanced  BOOLEAN,
    volte         BOOLEAN,
    sim_physical  SMALLINT,
    esim_count    SMALLINT,
    nfc           BOOLEAN,
    bluetooth_ver NUMERIC(3,1),
    wifi_gen      SMALLINT,
    n_nav_systems SMALLINT,
    ir_port       BOOLEAN
);

CREATE TABLE smartphones.phone_features (
    phone_id         INTEGER PRIMARY KEY REFERENCES smartphones.phone (phone_id),
    otg              BOOLEAN,
    fm_radio         BOOLEAN,
    memory_card_slot BOOLEAN,
    stereo_speakers  BOOLEAN,
    gms              BOOLEAN,
    headphone_jack   BOOLEAN,
    face_unlock      BOOLEAN,
    fingerprint      BOOLEAN
);
